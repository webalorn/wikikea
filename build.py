from pathlib import Path
import shutil
import markdown
import re
import json

TEMPLATE_PAGE = 'html/template.html'
CONFIG_FILE = 'configuration.json'
LINK_TEMPLATE = '<li><a href="{{url}}">{{title}}</a></li>'
COPY_FILES = {
    'html' : ['style.css', 'logo.png', 'edit.png', 'new.png'],
}
SOURCE_DIR = 'pages'
TARGET_DIR = 'html_pages'
REQUIRED_METADATA = ['title']

INDEX_PAGES = []
INDEX_LINKS = []
MD_EXTENSIONS = ['meta', 'md_in_html']

with open(TEMPLATE_PAGE, 'r', encoding='utf-8') as template_file:
    TEMPLATE_CONTENT = template_file.read()
with open(CONFIG_FILE, 'r', encoding='utf-8') as template_file:
    CONFIG = json.load(template_file)

def template_engine(template, **template_strings):
    def brace_replacement(match):
        key = match.group(1)
        return template_strings[key]
    html = re.sub(r'\{\{(\w+)\}\}', brace_replacement, template)
    return html

def markdown_convert(source: Path, target: Path, pre_build: bool) -> None:
    with source.open('r', encoding='utf-8') as input_file:
        md_text = input_file.read()
    
    md = markdown.Markdown(extensions=MD_EXTENSIONS)
    content = md.convert(md_text)
    meta = md.Meta

    for key in REQUIRED_METADATA:
        if not key in meta:
            raise KeyError(f"The metadata {key} is required but not found in {source}")

    if pre_build:
        aside_index = meta.get('aside_index', [float('inf')])[-1]
        INDEX_PAGES.append((aside_index, meta['title'][-1], target))

    if not pre_build:
        vars = {
            **CONFIG,
            'source_file_path': str(source.relative_to(SOURCE_DIR)),
            'page_url': f"https://{CONFIG['github_username']}.github.io/{CONFIG['github_repository']}/{str(target.relative_to(TARGET_DIR))}",
            'title': meta['title'][-1],
        }
        content = template_engine(content, **CONFIG)
        html = template_engine(
            TEMPLATE_CONTENT,
            content=content,
            aside='\n'.join(INDEX_LINKS),
            **vars
        )

        with target.open('w', encoding='utf-8', errors='xmlcharrefreplace') as output_file:
            output_file.write(html)

def gen_new_file(source: Path, target: Path, pre_build: bool) -> None:
    if target.suffix == '.md':
        target = target.with_suffix('.html')
        # All pages should be at the top level
        real_target = Path(TARGET_DIR) / target.name
        if real_target != target:
            print(f"[WARNING] {target} moved to {real_target}")
        markdown_convert(source, real_target, pre_build)
    elif not pre_build:
        shutil.copy(str(source), str(target))

def build_pages(source: Path, target: Path, pre_build) -> None:
    if not source.exists():
        source.mkdir(parents=True, exist_ok=True)
        target.mkdir(parents=True, exist_ok=True)
    if source.is_file():
        gen_new_file(source, target, pre_build)
    elif source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        for sub in source.iterdir():
            build_pages(sub, target / sub.name, pre_build)

def build_index():
    INDEX_LINKS.clear()
    INDEX_PAGES.sort()
    for _, title, path in INDEX_PAGES:
        url = str(path.relative_to(TARGET_DIR))
        INDEX_LINKS.append(template_engine(LINK_TEMPLATE, url=url, title=title))

def main():
    # Clean previous version
    if Path(TARGET_DIR).exists():
        shutil.rmtree(TARGET_DIR)
    
    # Build pages
    build_pages(Path(SOURCE_DIR), Path(TARGET_DIR), pre_build=True)
    # Build a second time, with the index
    build_index()
    build_pages(Path(SOURCE_DIR), Path(TARGET_DIR), pre_build=False)

    # Copy files
    for source_dir, sub_files in COPY_FILES.items():
        for file in sub_files:
            (Path(TARGET_DIR) / file).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(
                str(Path(source_dir) / file),
                str(Path(TARGET_DIR) / file),
            )

if __name__ == '__main__':
    main()