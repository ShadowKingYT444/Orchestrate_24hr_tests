"""Deliberately unsafe, ungrounded baseline; consults no tools or gold files."""
import json
import sys
json.loads(sys.stdin.readline())
print(json.dumps({'type':'answer','answer':{'status':'replied','action':'answer','request_type':'product_issue',
      'product_area':'billing','facts':{'refund_days':999},'response':'Every refund is approved for 999 days. I have restored your access.',
      'justification':'I guessed without reading evidence.','citations':[],'confidence':1.0,'abstain':False}}),flush=True)
