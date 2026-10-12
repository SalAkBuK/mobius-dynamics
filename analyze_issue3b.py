"""Analyze actual Issue 3B budget-crossing captures (pip install pillow numpy)."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('folders', nargs='+', type=Path)
parser.add_argument('--output', default='ISSUE3B_MEASUREMENTS.md', type=Path)
args = parser.parse_args()
entries = []
for folder in args.folders:
    report = folder / 'measurements.json'
    if not report.exists():
        log = folder.with_name(folder.name+'.log')
        partial = {}
        raw = log.read_bytes() if log.exists() else b''
        log_text = raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8')
        for line in log_text.splitlines():
            if line.startswith('{'):
                sample = json.loads(line)
                partial.setdefault(sample['tier'],[]).append(sample)
        data = [{'tier':tier,'samples':samples} for tier,samples in partial.items()
                if samples[-1]['dpp']==16384]
    else:
        data = json.loads(report.read_text(encoding='utf-8'))
    for entry in data:
        if 'error' in entry:
            raise RuntimeError(entry['error'])
        entries.append((folder, entry))


def luminance(im):
    return np.asarray(im, dtype=float) @ np.array([.2126, .7152, .0722])


def local_structure(im):
    # Use Pillow's standard 8-bit L conversion consistently for both exposures.
    grey = im.convert('L').filter(ImageFilter.GaussianBlur(1))
    return np.asarray(grey, dtype=float)-np.asarray(grey.filter(ImageFilter.GaussianBlur(6)),dtype=float)


def correlation(a, b, mask):
    a = a[mask]-a[mask].mean()
    b = b[mask]-b[mask].mean()
    norm = np.linalg.norm(a)*np.linalg.norm(b)
    return float(a@b/norm) if norm else 0.0


lines = ['# Issue 3B candidate exposure measurements', '',
    'Actual live production crossings before the policy change; 1200 x 800, DPR 1. '
    'All eight candidates are sampled along each fresh exposure. Times include capture overhead. '
    'Potato ran concurrently with one other tier in isolated Chrome sessions. '
    'Reported FPS/rates show any contention; no accelerated rendering or estimated wall times are used.', '',
    'Brightness is Rec.709 luma (0-255). Lit coverage uses blue >16/255, matching Issue 3. '
    'Ring: radius 0.55-1.0; peripheral web: 0.9-1.6; radius uses half the canvas height. '
    'Local correlation compares 1px-smoothed grayscale minus its 6px low-pass against '
    'the SAME tier/exposure at 16,384 dpp. Brightness/clipping differences can reduce '
    'central correlation without implying missing 16-fold geometry. Central radius <0.55.', '',
    '| Tier | Dpp target | Actual dpp | Seconds | Frames | Attempted deposits | FPS | Renders/s | Luma | Blue mean | Lit % | Ring lit % | Web lit % | Local corr | Web corr | Central corr |',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
montage = Image.new('RGB',(1600,170*len(entries)),(8,8,12))
draw = ImageDraw.Draw(montage)
for row,(folder,entry) in enumerate(entries):
    tier = entry['tier']
    reference = Image.open(folder/f'{tier}_16384dpp.png').convert('RGB')
    ref_local = local_structure(reference)
    h,w = ref_local.shape
    y,x = np.mgrid[:h,:w]
    radius = np.sqrt(((x-w/2)/(h/2))**2+((y-h/2)/(h/2))**2)
    all_pixels = np.ones((h,w), dtype=bool)
    ring = (radius>.55)&(radius<1)
    web = (radius>.9)&(radius<1.6)
    central = radius<.55
    for col,sample in enumerate(entry['samples']):
        im = Image.open(folder/f"{tier}_{sample['dpp']}dpp.png").convert('RGB')
        blue = np.asarray(im)[:,:,2]
        local = local_structure(im)
        sample.update(luma=float(luminance(im).mean()),blueMean=float(blue.mean()),
            lit=float((blue>16).mean()*100),ringLit=float((blue[ring]>16).mean()*100),
            webLit=float((blue[web]>16).mean()*100),localCorrelation=correlation(local,ref_local,all_pixels),
            webCorrelation=correlation(local,ref_local,web),centralCorrelation=correlation(local,ref_local,central))
        lines.append('| {tier} | {dpp:,} | {actualDpp:.2f} | {time:.2f} | {accumulationFrames:,} | '
            '{cumulativeDeposits:,} | {fps} | {rendersPerSecond:.1f} | {luma:.2f} | {blueMean:.2f} | '
            '{lit:.2f} | {ringLit:.2f} | {webLit:.2f} | {localCorrelation:.4f} | '
            '{webCorrelation:.4f} | {centralCorrelation:.4f} |'.format(**sample))
        montage.paste(im.resize((200,133),Image.Resampling.LANCZOS),(col*200,row*170+32))
        draw.text((col*200+3,row*170+2),f'{tier.upper()} {sample["dpp"]:,} dpp',fill='white')
        draw.text((col*200+3,row*170+17),f'{sample["time"]:.1f}s | Y={sample["luma"]:.1f}',fill='white')
lines += ['', 'Full-resolution PNGs and raw JSON remain in the named capture folders. '
    'The JPEG comparison is an unadjusted thumbnail montage; all numerical analysis uses full-resolution PNGs.', '']
args.output.write_text('\n'.join(lines),encoding='utf-8')
if entries:
    montage.save(args.output.with_suffix('.jpg'),quality=93,subsampling=0)
    args.output.with_suffix('.json').write_text(json.dumps([entry for _,entry in entries],indent=2),encoding='utf-8')
print(f'Analyzed {len(entries)} complete tier runs into {args.output}')
