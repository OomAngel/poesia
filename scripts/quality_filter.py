#!/usr/bin/env python3
"""Quality-filter the master training corpus by syllable accuracy."""
import json
from collections import Counter
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from poesia.phonology.spanish import SpanishPhonology
phonology = SpanishPhonology()

input_path = 'seeds/poetry_corpus/training_data_structured/master_train.jsonl'
output_path = 'seeds/poetry_corpus/training_data_structured/master_train_filtered.jsonl'
sonetos_only = 'seeds/poetry_corpus/training_data_structured/master_sonetos.jsonl'

passed = 0
failed = 0
total = 0
by_form = Counter()

targets = {'soneto': 11, 'haiku': 7, 'romance': 8, 'decima': 8,
           'cuarteto': 11, 'quintilla': 11}

with open(input_path) as fin, open(output_path, 'w') as fout, open(sonetos_only, 'w') as fson:
    for line in fin:
        r = json.loads(line)
        total += 1
        text = r['completion']
        lines = [l.strip() for l in text.split(chr(10)) if l.strip()]
        form = r.get('form', 'unknown')
        target = targets.get(form, 11)
        good = 0
        for l in lines:
            try:
                scan = phonology.scan_line(l)
                if abs(scan.metrical_syllable_count - target) <= 2:
                    good += 1
            except Exception:
                pass
        accuracy = good / len(lines) if lines else 0
        if accuracy >= 0.4:
            passed += 1
            by_form[form] += 1
            fout.write(json.dumps(r, ensure_ascii=False) + chr(10))
            if form == 'soneto':
                fson.write(json.dumps(r, ensure_ascii=False) + chr(10))
        else:
            failed += 1
        if total % 1000 == 0:
            print(f'  {total}... ({passed} passed)')

print(f'Total: {total}')
print(f'Passed: {passed}')
print(f'Failed: {failed}')
print(f'Pass rate: {passed/total*100:.1f}%')
print(f'By form: {dict(by_form.most_common())}')
print(f'Filtered file: {os.path.getsize(output_path)/1e6:.1f} MB')
