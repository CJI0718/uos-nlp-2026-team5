"""Fetch missing public PDFs once. Default: plan only; no model calls or retries."""
import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--ids', nargs='+')
    args = parser.parse_args()
    papers = json.loads((ROOT / 'paper_library.json').read_text(encoding='utf-8'))['papers']
    if args.ids:
        missing = set(args.ids) - {p['id'] for p in papers}
        if missing:
            parser.error('Unknown IDs: ' + ', '.join(sorted(missing)))
        papers = [p for p in papers if p['id'] in args.ids]
    downloaded = ROOT / 'papers_downloads'
    planned = 0
    for paper in papers:
        target = downloaded / Path(paper['file']).name
        original = ROOT / paper['file']
        existing = original if original.exists() else target
        if existing.exists():
            if hashlib.sha256(existing.read_bytes()).hexdigest() != paper['sha256']:
                raise SystemExit(f'{paper["id"]}: existing SHA-256 differs; inspect before continuing.')
            print(paper['id'], 'reuse verified file')
            continue
        url = paper.get('download_url')
        if not url:
            print(paper['id'], 'open official source:', paper.get('corrected_url', paper['url']))
            continue
        planned += 1
        print(paper['id'], 'download' if args.execute else 'planned', url, flush=True)
        if not args.execute:
            continue
        downloaded.mkdir(exist_ok=True)
        request = urllib.request.Request(url, headers={'User-Agent': 'UOS-NLP-Team5-literature-reader/1.0'})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                content = response.read(50 * 1024 * 1024 + 1)
        except Exception as error:
            raise SystemExit(f'{paper["id"]}: {type(error).__name__}: {error}; stopped, no retry.')
        if len(content) > 50 * 1024 * 1024 or not content.startswith(b'%PDF-'):
            raise SystemExit(f'{paper["id"]}: not a PDF within the size limit; open its official page. Stopped.')
        if hashlib.sha256(content).hexdigest() != paper['sha256']:
            candidate = target.with_suffix('.unverified.pdf')
            if candidate.exists():
                raise SystemExit(f'{paper["id"]}: previous unverified download exists; inspect it. No overwrite.')
            candidate.write_bytes(content)
            raise SystemExit(f'{paper["id"]}: PDF version differs; saved {candidate.name} for inspection. Stopped.')
        target.write_bytes(content)
        print(paper['id'], 'saved; SHA-256 matched', flush=True)
        time.sleep(3)
    print('Public downloads requested/planned:', planned)


if __name__ == '__main__':
    main()
