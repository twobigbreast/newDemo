#!/usr/bin/env python3
"""Read-only local inventory. No installs, network, secrets or automatic migration."""
import argparse, json, shutil
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, help='Optional JSON report path')
    args = parser.parse_args()
    root = args.repo.resolve()
    if not root.is_dir():
        parser.error('Repository directory does not exist')
    files = []
    for folder in ['source', 'scripts', 'dist']:
        base = root / folder
        if not base.is_dir():
            continue
        for path in base.rglob('*'):
            if path.is_symlink() or not path.is_file():
                continue
            rel = path.relative_to(root)
            if any(part in {'node_modules', '.git', '__pycache__'} for part in rel.parts):
                continue
            files.append((path, str(rel), path.stat().st_size))
    large = sorted(({'path': rel, 'bytes': size} for _, rel, size in files
                    if size >= 512 * 1024), key=lambda item: item['bytes'], reverse=True)
    sources = []
    for path, rel, size in files:
        if path.suffix not in {'.py', '.js', '.mjs', '.ts', '.tsx'} or size > 1024 * 1024:
            continue
        content = path.read_text(errors='replace')
        terms = ['skia', 'ffmpeg', 'base64', 'BUCKET', 'Range', 'FixedLengthStream']
        hits = [term for term in terms if term.lower() in content.lower()]
        if hits:
            sources.append({'path': rel, 'signals': hits})
    fonts = Path('/usr/share/fonts/opentype/noto')
    worker = root / 'dist/server/index.js'
    result = {
        'tools': {name: shutil.which(name) for name in ['ffmpeg', 'ffprobe', 'python', 'node']},
        'hosting_manifest_present': (root / '.openai/hosting.json').is_file(),
        'worker_bytes': worker.stat().st_size if worker.is_file() else None,
        'largest_files': large[:30],
        'implementation_candidates': sources,
        'noto_cjk_font_candidates': [str(p) for p in fonts.glob('*CJK*')] if fonts.is_dir() else [],
        'next_checks': [
            'Inspect the build/routing signals; this scan cannot prove files are served safely.',
            'Large Base64 literals can exhaust startup memory even with lazy request decoding.',
            'Reuse project environment/model caches; check actual font glyphs in keyframes.',
            'Do not treat any worker_bytes value as a universal safe deployment threshold.',
        ],
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n')
    else:
        print(text)

if __name__ == '__main__':
    main()
