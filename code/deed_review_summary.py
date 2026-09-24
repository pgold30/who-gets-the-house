"""Deed-image review of the same-surname flag (v3.1).

Reads audit/deed_image_review/deed_review_readings.csv: a random sample
(seed 20260924) of 40 flagged and 20 unflagged cash endpoint deeds from the
headline house sample, read from ACRIS images with AI assistance and confirmed
by the author. A deed counts as showing a non-market sign when its RP-5217NYC
transfer report declares a sale between relatives (box A), a buyer who is also
a seller (box C) or a non-standard deed type (box E), or reports a $0 price with
no transfer tax. Wilson 95% intervals; the sample is small and self-declared
conditions are a lower bound.
"""
import csv, json, math
from analyze_repeat_sales import ROOT, OUT


def wilson(k, n, z=1.96):
    p = k / n; c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [c - h, c + h]


def main():
    rows = list(csv.DictReader(open(ROOT / 'audit/deed_image_review/deed_review_readings.csv')))
    assert len(rows) == 60 and all(r['human_confirmation_date'] for r in rows)
    res = {}
    for key, flag in [('flagged', 'True'), ('unflagged', 'False')]:
        sub = [r for r in rows if r['flagged'] == flag]; n = len(sub)
        yes = sum(r['clearly_non_arms_length'] == 'yes' for r in sub)
        pos = sum(r['clearly_non_arms_length'] == 'possible' for r in sub)
        box_a = sum('box A' in r['stated_relationship'] for r in sub)
        res[key] = {'n': n, 'non_market_sign': yes, 'share': yes / n, 'ci': wilson(yes, n),
                    'with_possible': yes + pos, 'share_with_possible': (yes + pos) / n, 'ci_with_possible': wilson(yes + pos, n),
                    'relatives_box_A': box_a}
    res['method'] = __doc__.strip()
    (OUT / 'deed_review_summary.json').write_text(json.dumps(res, indent=2))
    F, U = res['flagged'], res['unflagged']
    pc = lambda v: f'{100 * v:.0f}'
    m = {'DeedN': F['n'], 'DeedYes': F['non_market_sign'], 'DeedShare': pc(F['share']), 'DeedCI': '[{}, {}]'.format(*map(pc, F['ci'])),
         'DeedPossible': F['with_possible'] - F['non_market_sign'], 'DeedShareWithPossible': pc(F['share_with_possible']),
         'DeedBoxA': F['relatives_box_A'], 'DeedUN': U['n'], 'DeedUYes': U['non_market_sign'], 'DeedUShare': pc(U['share']),
         'DeedUCI': '[{}, {}]'.format(*map(pc, U['ci'])), 'DeedUBoxA': U['relatives_box_A']}
    (ROOT / 'paper/generated/deed_numbers.tex').write_text('\n'.join('\\newcommand{\\%s}{%s}' % (k, v) for k, v in m.items()) + '\n')
    print(json.dumps(m), flush=True)


if __name__ == '__main__':
    main()
