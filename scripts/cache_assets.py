"""Cache published, verified remote images locally; preserve source on failure."""
import hashlib
from common import ROOT, read, write
from harvest import download

def main():
    figures = read('figures.json')
    out = ROOT / 'site' / 'assets' / 'figures'
    out.mkdir(parents=True, exist_ok=True)
    for figure in figures:
        if figure.get('status') != 'published' or not figure.get('publication_verified'):
            continue
        url = figure.get('image','')
        if not url.startswith('https://'):
            continue
        try:
            data = download(url,8_000_000)
            if data.startswith(b'\x89PNG\r\n\x1a\n'):
                ext = '.png'
            elif data.startswith(b'\xff\xd8\xff'):
                ext = '.jpg'
            else:
                raise ValueError('not a supported PNG/JPEG image')
            name = hashlib.sha256(url.encode()).hexdigest()[:20] + ext
            (out/name).write_bytes(data)
            figure.update(image='assets/figures/'+name,original_image=url)
            print(figure['id'] + ': cached')
        except Exception as exc:
            print(figure['id'] + ': retaining original link (' + type(exc).__name__ + ')')
    write('figures.json',figures)

if __name__ == '__main__': main()
