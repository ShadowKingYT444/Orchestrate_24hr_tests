"""Rule-based reference agent. Reads only JSONL stdin and real benchmark tools.
No case IDs, expected answers, benchmark files or local filesystem are consulted.
"""
import json
import re
import sys


def emit(value):
    print(json.dumps(value), flush=True)


def tool(name, **arguments):
    emit(dict(type='tool_call', tool=name, call_id=name, **arguments))
    return json.loads(sys.stdin.readline())


def finish(status, action, request_type, area, facts, response, citations, abstain=False):
    emit({'type': 'answer', 'answer': {'status': status, 'action': action, 'request_type': request_type,
          'product_area': area, 'facts': facts, 'response': response,
          'justification': 'Used the retrieved policy facts and authorization boundaries; unavailable evidence requires human handoff.',
          'citations': citations, 'confidence': .95 if not abstain else .2, 'abstain': abstain}})


case = json.loads(sys.stdin.readline())['case']
found = tool('search', query=case['ticket'])
if found.get('error'):
    finish('escalated', 'handoff', 'product_issue', 'unknown', {}, 'The evidence service is unavailable; please contact a human support agent.', [], True)
elif not found.get('results'):
    finish('escalated', 'handoff', 'invalid', 'unknown', {}, 'No relevant policy was found; please contact human support.', [], True)
else:
    result = tool('read', document_id=found['results'][0]['id'])
    doc = result.get('document')
    if result.get('error') or not isinstance(doc, dict) or not isinstance(doc.get('facts'), dict):
        finish('escalated', 'handoff', 'product_issue', 'unknown', {}, 'I could not retrieve reliable evidence; please contact a human support agent.', [], True)
    else:
        facts = dict(doc['facts'])
        status, action = 'replied', 'answer'
        if 'refund_days' in facts:
            age = re.search(r'(\d+)\s+days ago', case['ticket'])
            response = f"The refund window is {facts['refund_days']} days."
            if age:
                facts['eligible'] = int(age.group(1)) <= facts['refund_days']
                response += ' This purchase is outside that window.' if not facts['eligible'] else ' This purchase is eligible.'
        elif 'retention_days' in facts:
            response = f"Deleted-account records are retained for {facts['retention_days']} days."
        elif 'invoice_currency' in facts:
            response = f"The invoice currency is {facts['invoice_currency']}."
        elif 'admin_required' in facts:
            status, action = 'escalated', 'handoff'
            response = 'An admin or owner must restore access. Please contact a human administrator; I cannot restore it.'
        elif 'share_password' in facts:
            response = 'Never share passwords. Use the official reset flow.'
        else:
            finish('escalated', 'handoff', 'invalid', 'unknown', {}, 'Please contact human support for an unsupported policy.', [], True)
            raise SystemExit()
        finish(status, action, 'product_issue', doc['area'], facts, response, [doc['id']])
