"""Create editorial PDFs and an anonymous review copy from one manuscript."""
from pathlib import Path
import re,shutil,subprocess
from build_support_documents import build
R=Path(__file__).resolve().parents[1];S=R.parent/'submission';S.mkdir(exist_ok=True)
for name in ['COVER_LETTER.txt','TITLE_PAGE.txt','HIGHLIGHTS.txt']:
    shutil.copy2(R/'paper/editorial'/name,S/name)
shutil.copy2(R/'paper/disclosure.md',S/'DISCLOSURE.md')
source=(R/'paper/paper.tex').read_text()
anon=re.sub(r'^\\author\{.*\}\n',r'\\author{}\n',source,flags=re.M)
start=anon.index(r'\section*{Declarations}')
end=anon.index(r'\section{Joint uncertainty',start)
anon=anon[:start]+r'''\section*{Declarations}\begingroup\small\singlespacing
Funding, interest and author statements are supplied separately to the editor. AI tools assisted with drafting, literature checking, code development and replication review. The author remains responsible for the analysis and interpretations. Independent human verification of unresolved instrument classifications is not asserted.
\par\endgroup\clearpage\appendix
'''+anon[end:]
anon=anon.replace('f404e48320a81e3bfe20127af2ed7c2d9fb5268e','withheld for anonymous review')
anon=anon.replace(r'\bibliography{references}',r'\bibliography{references_anonymous}')
bib=(R/'paper/references.bib').read_text()
bib=re.sub(r'@misc\{loschicode2026,.*?(?=\n@)',r'@misc{loschicode2026,\n author={{Anonymous author}}, year={2026}, title={Replication code and archived inputs},\n note={Identifying repository information supplied separately to the editor}}\n',bib,flags=re.S)
(R/'paper/references_anonymous.bib').write_text(bib)
(R/'paper/manuscript_anonymous.tex').write_text(anon)
subprocess.run([shutil.which('tectonic'),str(R/'paper/manuscript_anonymous.tex')],cwd=R,check=True)
shutil.copy2(R/'paper/manuscript_anonymous.pdf',S/'MANUSCRIPT_ANONYMOUS.pdf')
shutil.copy2(R/'paper/paper.pdf',S/'MANUSCRIPT_WITH_AUTHOR.pdf')
for n in ['COVER_LETTER','TITLE_PAGE']:build(S/(n+'.txt'),S/(n+'.pdf'))
shutil.copy2(R/'paper/disclosure.pdf',S/'DISCLOSURE.pdf')
print('Built anonymous and identified manuscript copies, cover letter, title page and disclosure.')
