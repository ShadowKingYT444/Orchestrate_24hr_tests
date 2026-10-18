import io
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from orchestrate_eval import archive


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'input.zip'

    def make(self, entries, compression=zipfile.ZIP_STORED):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.path, 'w', compression=compression) as output:
                for name, content in entries:
                    output.writestr(name, content)
        return self.path

    def assert_bad(self, text=None):
        report = archive.inspect_archive(self.path)
        self.assertEqual(report['status'], 'fail', report)
        self.assertTrue(report['issues'])
        if text:
            self.assertIn(text, ' '.join(report['issues']))
        destination = self.root / 'output'
        with self.assertRaises(ValueError):
            archive.safe_extract(self.path, destination)
        self.assertFalse(destination.exists())
        self.assertEqual(list(self.root.glob('.zip-extract-*')), [])
        return report

    def test_valid_archive_extract(self):
        self.make([('dir/', ''), ('dir/readme.txt', 'hello'), ('main.py', 'raise Exception("never execute")')])
        report = archive.inspect_archive(self.path)
        self.assertEqual(report['status'], 'pass', report)
        self.assertEqual(report['files'], 3)
        self.assertEqual(report['size_bytes'], self.path.stat().st_size)
        output = self.root / 'output'
        self.assertEqual(archive.safe_extract(self.path, output), report)
        self.assertEqual((output / 'dir/readme.txt').read_text(), 'hello')

    def test_unsafe_paths(self):
        for name in ('../outside', '/absolute', 'C:/windows', 'C:relative', 'dir\\file',
                     'a/../../x', 'a//b', './file', 'a/../b', 'foo./bar', 'NUL.txt'):
            with self.subTest(name=name):
                self.make([(name, 'x')])
                self.assert_bad()

    def test_symlink_and_special(self):
        for kind in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFSOCK):
            with self.subTest(kind=kind):
                info = zipfile.ZipInfo('link')
                info.create_system = 3
                info.external_attr = (kind | 0o777) << 16
                self.make([(info, '../outside')])
                self.assert_bad('special')

    def test_duplicate_and_case_collision(self):
        for first, second in [('file', 'file'), ('FILE', 'file'), ('DIR/a', 'dir/b'), ('é', 'e\u0301')]:
            with self.subTest(first=first, second=second):
                self.make([(first, 'a'), (second, 'b')])
                self.assert_bad()

    def test_file_parent_collision(self):
        self.make([('dir', 'a'), ('dir/file', 'b')])
        self.assert_bad('collision')

    def test_credentials(self):
        for name in ('.env', '.env.production', 'a/credentials.json', 'secrets.txt', 'id_rsa', 'key.pem', '.aws/config'):
            with self.subTest(name=name):
                self.make([(name, 'sensitive')])
                self.assert_bad('credential')

    def test_nested_archive_name_and_magic(self):
        for name, content in [('nested.zip', b'anything'), ('innocent.txt', b'PK\x03\x04hidden')]:
            with self.subTest(name=name):
                self.make([(name, content)])
                self.assert_bad('Nested archive')

    def test_corrupt_and_crc(self):
        self.path.write_bytes(b'not a zip')
        self.assert_bad('validation')
        self.make([('hello.txt', 'unique payload')])
        data = self.path.read_bytes().replace(b'unique payload', b'unique payloae', 1)
        self.path.write_bytes(data)
        self.assert_bad('CRC')

    def test_truncated(self):
        self.make([('hello.txt', 'hello')])
        self.path.write_bytes(self.path.read_bytes()[:-12])
        self.assert_bad()

    def test_size_and_count_limits(self):
        self.make([('a', b'a' * 100), ('b', 'b')])
        for limit, value, issue in [('MAX_ZIP_BYTES', 10, 'compressed size'),
                                    ('MAX_EXPANDED_BYTES', 100, 'expanded size'),
                                    ('MAX_FILES', 1, 'member count')]:
            with self.subTest(limit=limit), patch.object(archive, limit, value):
                self.assert_bad(issue)

    def test_forged_directory_count(self):
        self.make([('a', 'a'), ('b', 'b')])
        data = bytearray(self.path.read_bytes())
        end = data.rfind(b'PK\x05\x06')
        struct.pack_into('<HH', data, end + 8, 1, 1)
        self.path.write_bytes(data)
        self.assert_bad('directory count')

    def test_directory_payload(self):
        self.make([('directory/', 'hidden content')])
        self.assert_bad('directory member')

    def test_compression_bomb_ratio(self):
        self.make([('bomb.txt', b'0' * 1_000_000)], zipfile.ZIP_DEFLATED)
        self.assert_bad('ratio')

    def test_unsupported_compression(self):
        self.make([('data.txt', 'x')])
        data = bytearray(self.path.read_bytes())
        struct.pack_into('<H', data, 8, 99)
        central = data.index(b'PK\x01\x02')
        struct.pack_into('<H', data, central + 10, 99)
        self.path.write_bytes(data)
        self.assert_bad('Unsupported compression')

    def test_encrypted_flag(self):
        self.make([('data.txt', 'x')])
        data = bytearray(self.path.read_bytes())
        struct.pack_into('<H', data, 6, 1)
        central = data.index(b'PK\x01\x02')
        struct.pack_into('<H', data, central + 8, 1)
        self.path.write_bytes(data)
        self.assert_bad('Encrypted')

    def test_refuse_existing_destinations(self):
        self.make([('data.txt', 'x')])
        for kind in ('directory', 'file', 'broken_symlink'):
            output = self.root / kind
            if kind == 'directory':
                output.mkdir()
            elif kind == 'file':
                output.write_text('keep')
            else:
                output.symlink_to(self.root / 'missing')
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                archive.safe_extract(self.path, output)
        self.assertEqual((self.root / 'file').read_text(), 'keep')

    def test_extraction_failure_cleans_temporary(self):
        self.make([('data.txt', 'x')])
        with patch.object(archive.shutil, 'copyfileobj', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                archive.safe_extract(self.path, self.root / 'output')
        self.assertFalse((self.root / 'output').exists())
        self.assertEqual(list(self.root.glob('.zip-extract-*')), [])

    def test_missing_input(self):
        self.assert_bad('validation')

    def test_submission_hygiene(self):
        self.make([('README.md', 'setup'), ('src/main.py', 'pass')])
        self.assertEqual(archive.inspect_submission_archive(self.path)['status'], 'pass')
        self.make([('src/main.py', 'pass')])
        self.assertIn('README', ' '.join(archive.inspect_submission_archive(self.path)['issues']))
        for folder in ('dataset', '.venv', 'node_modules', '__pycache__', 'build', 'dist', '.git'):
            with self.subTest(folder=folder):
                self.make([('README.md', 'setup'), (folder + '/data', 'exclude')])
                self.assertEqual(archive.inspect_submission_archive(self.path)['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
