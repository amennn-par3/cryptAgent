"""Build the human-readable CryptAgent presentation guide from verified project facts."""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate,
                                Paragraph, Preformatted, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'CRYPTAGENT_PRESENTATION_GUIDE.pdf'
FONT = Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('DejaVu', str(FONT / 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('DejaVu-Bold', str(FONT / 'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFont(TTFont('DejaVuMono', str(FONT / 'DejaVuSansMono.ttf')))

ink = colors.HexColor('#17243a')
blue = colors.HexColor('#254fa0')
muted = colors.HexColor('#526277')
light = colors.HexColor('#eef3fa')
rule = colors.HexColor('#d8e1ed')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Cover', fontName='DejaVu-Bold', fontSize=24, leading=30,
                          textColor=ink, spaceAfter=14))
styles.add(ParagraphStyle(name='Deck', fontName='DejaVu', fontSize=12, leading=18,
                          textColor=muted, spaceAfter=18))
styles.add(ParagraphStyle(name='H1x', fontName='DejaVu-Bold', fontSize=15, leading=20,
                          textColor=blue, spaceBefore=16, spaceAfter=8, keepWithNext=True))
styles.add(ParagraphStyle(name='H2x', fontName='DejaVu-Bold', fontSize=11, leading=16,
                          textColor=ink, spaceBefore=10, spaceAfter=5, keepWithNext=True))
styles.add(ParagraphStyle(name='Bodyx', fontName='DejaVu', fontSize=9.1, leading=14,
                          textColor=ink, spaceAfter=7))
styles.add(ParagraphStyle(name='Smallx', fontName='DejaVu', fontSize=8, leading=12,
                          textColor=muted, spaceAfter=6))
styles.add(ParagraphStyle(name='Bulx', fontName='DejaVu', fontSize=9, leading=14,
                          leftIndent=13, firstLineIndent=-9, textColor=ink, spaceAfter=4))
styles.add(ParagraphStyle(name='Cellx', fontName='DejaVu', fontSize=8.1, leading=12,
                          textColor=ink))
styles.add(ParagraphStyle(name='Headcell', fontName='DejaVu-Bold', fontSize=8.3, leading=12,
                          textColor=colors.white))
styles.add(ParagraphStyle(name='Boxx', fontName='DejaVuMono', fontSize=8.1, leading=12,
                          textColor=ink, backColor=light, leftIndent=8, rightIndent=8,
                          borderPadding=7, spaceBefore=5, spaceAfter=9))

story = []
def P(value, style='Bodyx'):
    story.append(Paragraph(value, styles[style]))
def H(value): P(escape(value), 'H1x')
def S(value): P(escape(value), 'H2x')
def B(value): P('• ' + value, 'Bulx')
def T(headers, rows, widths):
    cells = [[Paragraph(escape(str(x)), styles['Headcell']) for x in headers]]
    cells += [[Paragraph(str(x), styles['Cellx']) for x in row] for row in rows]
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),blue), ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,light]),
        ('LINEBELOW',(0,0),(-1,0),0.5,blue),
        ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LINEBELOW',(0,1),(-1,-1),0.3,rule)]))
    story.append(table)
    story.append(Spacer(1,5))
def C(value):
    story.append(Preformatted(value, ParagraphStyle(name='Code'+str(len(story)),
        parent=styles['Boxx'], fontName='DejaVuMono', fontSize=7.2, leading=10.6)))

P('CryptAgent', 'Cover')
P('Presentation and study guide — the current AES source reviewer, its history, architecture, model, dataset, validation and next steps', 'Deck')
P('<b>Snapshot:</b> 2 October 2026. This guide describes files in this local checkout. The active web app can change later; check the repository status before presenting.', 'Smallx')

H('1. A two-minute explanation you can read aloud')
P('“CryptAgent is our BTP project for reviewing cryptographic integration code. The current demonstration focuses on one fixed case: C++20 code using Windows CNG for AES-128-GCM. We check five requirements: functional correctness, rejection of tampering, no plaintext release before authentication, correct key/nonce/tag handling, and safe input/output boundaries. The user pastes code into a local web page. A Node.js backend validates it, sends it only to a Llama model running on the same machine, checks the model’s structured response and source-line references, and returns an advisory report. A small deterministic source scanner adds clearly labeled observations. The pipeline runs, but this is source review, not native Windows execution or a security certificate. An experimental AES adapter was trained and compared with the base model; it improved output validity more than defect detection and is not deployed. CKKS, TFHE and BFV research fixtures support the planned multi-profile expansion.”')
P('<b>One-sentence version:</b> CryptAgent currently turns a pasted CNG AES-GCM C++ excerpt into a local, source-linked review with explicit uncertainty.', 'Smallx')

H('2. What problem we are solving')
P('A cryptographic algorithm may be sound while an application uses its API incorrectly. For example, a program may ignore an authentication failure, publish decrypted bytes too early, reuse a nonce with the same key, pass the wrong tag length, or advertise more output capacity than it allocated. CryptAgent concentrates on these integration mistakes. Its current threat model allows an attacker to modify encrypted input and observe public results, but not read the secret key.')
P('The words <b>verify</b> and <b>model</b> need care in the presentation. Today the browser delivers an advisory source-code review. It does not compile the submitted code, execute attacks, mathematically prove correctness, or confirm that a snippet is deployable. A model’s “no issue identified” means only that the model found none in the visible text.')

H('3. AES-128-GCM in practical terms')
P('<b>AES</b> is a symmetric block cipher: encryption and decryption use the same secret key. <b>GCM</b> is an authenticated encryption mode. It gives confidentiality through encryption and an authentication tag to detect changes to the ciphertext and any associated authenticated data (AAD). The fixed CryptAgent profile uses a 16-byte AES key (128 bits), a 12-byte nonce and a 16-byte tag.')
P('Conceptually, encryption takes <b>key + fresh nonce + plaintext + optional AAD</b> and returns <b>ciphertext + tag</b>. Decryption takes <b>key + nonce + ciphertext + AAD + tag</b> and must check the tag before accepting plaintext. AAD is bound to the message but is not itself encrypted. A nonce must not be repeated for encryption under the same key. A zero-initialized nonce buffer alone is not proof of reuse: the code may fill it with a fresh value before encryption.')
P('On Windows CNG, code selects the AES algorithm and GCM chaining mode, creates a key handle, initializes <font name="DejaVuMono">BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO</font>, and supplies its nonce, AAD and tag fields to <font name="DejaVuMono">BCryptEncrypt</font> or <font name="DejaVuMono">BCryptDecrypt</font>. The return status matters: a tag mismatch is an authentication failure. CryptAgent reviews the caller’s handling of these fields and the result; the current Linux service does not run CNG itself.')
T(['Part','What the reviewer checks'],[
    ('Key / 16 bytes','Does the visible integration meet the AES-128 profile and handle key creation or import safely?'),
    ('Nonce / 12 bytes','Is each encryption nonce fresh under the same key, and is the correct size passed to CNG?'),
    ('Tag / 16 bytes','Is a tag supplied and checked with the configured length?'),
    ('AAD','When the application contract requires AAD, is the same data authenticated on both paths?'),
    ('Status and output','Does failed decryption return failure without exposing plaintext?')],
    [37*mm,135*mm])

H('4. Fixed scope and five requirements')
P('The active profile is <font name="DejaVuMono">aes128-gcm-tampering-v1</font> in <font name="DejaVuMono">profiles/aes128_gcm_tampering.json</font>. The page displays AES-128-GCM, C++20 / Windows CNG and message tampering. There is no scheme, library, attacker or language selector in this midterm flow.')
T(['ID','Requirement','What a relevant source finding could look like'],[
    ('F01','Functional correctness','A supported input, including a documented boundary case, is handled incorrectly.'),
    ('F02','Tampering rejection','The wrapper fails to reject a modified ciphertext, nonce, tag or required AAD.'),
    ('F03','Authentication before output','The status is ignored or caller output is populated before authentication succeeds.'),
    ('F04','Key, nonce and tag handling','Wrong profile size, repeated encryption nonce or missing tag configuration.'),
    ('F05','Input/output boundaries','Unchecked length conversion, underflow, or a CNG capacity larger than the buffer.')],
    [14*mm,47*mm,111*mm])
P('The profile assumes a trusted operating system and CNG implementation, an attacker without the secret key, and observable public status/output. Replay prevention, physical/timing side channels and universal memory-safety proofs are outside this version.')

H('5. What was built before the current web app')
P('The repository preserves the original Phase 1–3 research: requirements and threat model; machine-readable schemas and a C++ contract; synthetic cases, a harness, and validation tools. Those historical files use a <b>different</b> profile: libsodium XChaCha20-Poly1305, with 13 contract requirements. A historical 150-case benchmark represents 30 scenario groups with shared ancestry; it is not 150 independent implementations. The older Windows validation document reports package/schema checks and a syntax-only C++ header check, while native libsodium candidate execution was not run because the dependency was missing. These facts are research history, not claims about the active AES/CNG web service.')
P('The present AES-only scope came later. Broader Rust/Python FHE, lattice and multi-scheme experiments remain stored in the repository or source folders. They are not selectable in the current app and are not suitable labels for this fixed AES/CNG reviewer.')

H('6. Architecture: how the pieces connect')
C('Browser  http://127.0.0.1:8000\n   | GET /api/status  -> profile + model state + session token\n   | POST /api/verify -> code + profile ID + verify mode\n   v\nNode backend (validation, source observations, report policy)\n   | GET /health + POST /review on fixed loopback address\n   v\nPython service  http://127.0.0.1:8081\n   | local cached Llama-3.1-8B-Instruct on CUDA GPU\n   v\nJSON answer -> strict validator -> report -> browser / JSON export')
P('The connection is an HTTP request inside the same machine. The backend hardcodes <font name="DejaVuMono">127.0.0.1:8081</font>; user input cannot select a remote model URL. The Python service and web server bind to loopback. There is no OpenAI API key, paid API call or normal external transmission of submitted source in this active path. The services do not persist submitted source, although an exported report contains quoted excerpts.')

H('7. Frontend: what the student uses')
P('<font name="DejaVuMono">frontend/index.html</font> defines the fixed-profile screen. <font name="DejaVuMono">frontend/styles.css</font> lays out the editor and result panel. <font name="DejaVuMono">frontend/app.js</font> handles interaction.')
B('<b>Status:</b> asks <font name="DejaVuMono">GET /api/status</font> for the profile, model health and a per-process session token; loading/error status refreshes automatically.')
B('<b>Input:</b> paste code or open a C++ source/header file; the editor shows line numbers and byte/line counts. File upload is local browser reading, not a cloud upload.')
B('<b>Review:</b> sends JSON with code, fixed profile ID and mode <font name="DejaVuMono">verify</font>. During review the editor locks and shows progress.')
B('<b>Result:</b> shows a headline, five requirement assessments, code quotations, clickable source line locations, model message and limitations. Export JSON downloads the report on the user’s machine.')
B('<b>Errors:</b> invalid or empty input, service failure and timeout are displayed explicitly. Unrelated code can receive “outside scope”; short snippets can receive “needs context.”')

H('8. Node backend: each module’s job')
T(['File','Responsibility'],[
    ('backend/app.mjs','Serves the page; issues a random session token; accepts only status and verify API routes; checks host/origin, JSON shape, profile, source limits and concurrency.'),
    ('backend/verifier.mjs','Runs a narrow pattern scanner, calls the model client, derives an overall advisory verdict, and constructs the version 2.0 report.'),
    ('backend/llm_client.mjs','Calls the fixed local Python endpoint, verifies service/model/revision/profile/prompt identity, bounds response size and time, and applies JSON validation.'),
    ('backend/review_contract.mjs','Requires the five F01–F05 assessments, consistent scope/findings and exact quotations in valid source lines.'),
    ('backend/native_checks.mjs','Marks every native check not_run; it does not execute user C++.')],
    [50*mm,122*mm])
P('The source-pattern scanner currently notices such text as a discarded <font name="DejaVuMono">BCryptDecrypt</font> call, a standalone decrypt call, a zero initializer near a nonce, some output-related identifiers and an ECB mode identifier. These are <b>observations</b>, not confirmed security defects. The model’s own findings are labeled separately.')
P('Input is limited to nonempty source with no null bytes, at most 64 KiB and 2,000 lines. The backend allows one active review. It returns explicit HTTP errors for malformed requests or busy status. The model client has a 110-second deadline, and the browser has a 125-second deadline. Invalid model JSON is rejected rather than silently treated as a pass.')

H('9. Local Llama: loading and inference')
P('<font name="DejaVuMono">backend/local_model.py</font> runs a Python HTTP service with <font name="DejaVuMono">GET /health</font> and <font name="DejaVuMono">POST /review</font>. It loads the cached <font name="DejaVuMono">meta-llama/Llama-3.1-8B-Instruct</font> base model at a pinned revision, in offline mode. PyTorch uses the NVIDIA CUDA GPU; Transformers and bitsandbytes load the model in 4-bit form with bfloat16 computation. This saves GPU memory. No AES adapter is loaded into the active service.')
P('For each request, Python combines the fixed review instructions, the fixed profile, and line-numbered untrusted source text into a Llama chat prompt. It rejects prompts above 3,072 input tokens without truncation. Generation is deterministic in configuration (<font name="DejaVuMono">do_sample=False</font>) and bounded by 1,536 new tokens or 90 seconds. A generation that stops at a time/token limit without an end token is marked incomplete. One review runs at a time. The service reports loading, ready, busy and error states.')
P('The local model is an <b>advisory reviewer</b>. Its JSON must contain a scope, exactly five checks and source-linked findings. The Node validator confirms formatting, cross-field consistency and quoted source location. It cannot determine whether every explanation is cryptographically correct. That is why fine-tuning, expert label review and independent tests matter.')

H('10. One code submission, step by step')
T(['Step','What happens'],[
    ('1','The page obtains the fixed profile, local model state and session token.'),
    ('2','The student pastes/uploads source and presses Review AES code.'),
    ('3','Node checks the request and normalizes line endings; it hashes the submitted source.'),
    ('4','A small scanner records source-pattern observations. Node asks local Llama to review the same source.'),
    ('5','Python returns JSON; Node validates five IDs, scope, status consistency and exact source quotations.'),
    ('6','Node combines validated model assessments and source observations into an advisory report.'),
    ('7','The page shows the report and can export its JSON. The candidate was not compiled or run.')],
    [17*mm,155*mm])
P('Example: a snippet calls <font name="DejaVuMono">BCryptDecrypt</font>, discards its return status and then returns success. The source scanner can flag the discarded-status line as a concern for F03. That observation invites review of authentication failure handling; it is not a native tampering witness.')

H('11. How to read a report')
P('The report records a profile ID/version/hash, source hash and line count, model identity and prompt hash, overall verdict, the five per-check assessments, findings with source lines and quotations, and explicit execution/formal-verification statuses. The possible overall verdicts are:')
T(['Verdict','Meaning'],[
    ('potential_issues','Source observations or model findings need human review.'),
    ('no_issues_identified','The model reported no concerns on visible source; not a proof or runtime pass.'),
    ('insufficient_context','The relevant implementation or caller context is missing.'),
    ('outside_scope','The model classified the submission outside the fixed Windows CNG AES-GCM profile.'),
    ('review_unavailable','Model unavailable, busy, incomplete or invalid; no model conclusion accepted.')],
    [47*mm,125*mm])
P('Each requirement can say potential issue, no issue identified, insufficient context, or not applicable for outside-scope code. A model issue without a valid source quotation is downgraded. The overall “potential issues” headline can come from a source observation even if the model wrongly says “no issue” on a specific check; the report shows both so the discrepancy is visible.')

H('12. Dataset and experimental fine-tuning')
P('Earlier project datasets include different cryptographic schemes and languages. Those are useful historical research materials but do not match the fixed AES/CNG runtime contract. A newer <b>candidate</b> AES source-review release is stored in <font name="DejaVuMono">training/aes_source_pilot_v1/data</font>: <b>22 train, 4 validation and 4 test = 30 unique code samples</b>. It contains 16 distinct short training snippets plus six related full-session variants; the rest are development checks. The examples cover ignored authentication status, early plaintext publication, nonce/key/tag sizes, nonce handling, buffer capacity, out-of-scope code and missing context.')
P('The release stores expected scope, F01–F05 assessments, explanations and exact source-linked quotations. The builder checked normalized duplicates, family membership across splits, production JSON validation, prompt hashes and the 3,072-token limit. The longest serialized training sample was 3,049 tokens. The training labels were authored from source review; no Windows native run validates them.')
P('<b>Current training status:</b> an explicitly experimental two-epoch AES LoRA pilot used 22 training rows and four validation rows, leaving four test rows untouched. Its manifest still says <font name="DejaVuMono">training_ready=false</font> because independent full-session label review and a fresh held-out split remain outstanding. The active web app still uses the cached base Llama model, not this adapter.')
P('The 20-case synthetic comparison is stored in <font name="DejaVuMono">evaluation/aes_pilot_20/REPORT.md</font>. Fully accepted reviews improved from 7/20 to 20/20, but correctly located targeted concerns were only 0/13 for the base and 3/13 for the adapter; both avoided false alarms on 3/4 targeted controls. This is exploratory source review, not a generalization or security-accuracy claim.')
P('The trainer (<font name="DejaVuMono">training/train.py</font>) performs offline assistant-output-only QLoRA fine-tuning with explicit dataset selection and hashes. It normally refuses draft releases; a restricted <font name="DejaVuMono">--experimental-draft</font> option was used for this AES pilot. Mixed-scheme records, truncated examples and existing output directories remain guarded. An adapter requires independent evaluation and explicit deployment before affecting the app.')

H('13. What has actually been tested')
P('For the AES web stack, 11 Node tests and four Python HTTP tests passed. They cover fixed routes, profile/input guards, local-only model calls, malformed or contradictory JSON, fake source quotations, offline/error behavior and response structure. Three synthetic live GPU smoke submissions returned complete reports: unrelated Python was outside scope; declarations needed more context; an ignored-decryption-status excerpt showed potential issues. These checks establish that the pipeline works, not that its security predictions are accurate.')
P('The base model missed the ignored-status concern on an individual F03 assessment; the source-pattern observation surfaced the overall potential issue. It also made optimistic “no issue” assessments for incomplete excerpts. A stricter prompt experiment made responses less reliable and was reverted. This is direct evidence for requiring better labels and a proper evaluation before presenting accuracy claims.')
P('There is currently no native Windows machine for CNG runtime verification. The active report explicitly marks candidate execution and formal verification <font name="DejaVuMono">not_run</font>. The legacy <font name="DejaVuMono">VALIDATION.md</font> records older Phase 1–3 checks on a historical Windows host; those are not current AES/CNG runtime results.')

H('14. Setup and machine notes')
P('On the current Linux laboratory machine, the application uses the existing Python environment at <font name="DejaVuMono">/home/hp/crypto-llm/.venv/bin/python</font> and a working NVIDIA RTX A4000 GPU with 16 GiB of memory. A CUDA tensor test succeeded. The app starts with <font name="DejaVuMono">bash start.sh</font>, which launches both Node and Python; Node serves port 8000 and Python serves 8081 on 127.0.0.1. The app also includes <font name="DejaVuMono">start.ps1</font> for Windows, but the active CNG runtime was not verified on Windows in this work.')
P('The repository ignores local model weights, adapters, checkpoints, executables and environments so they are not committed to ordinary Git history. It does not use the OpenAI API. If the cached Llama weights, CUDA environment or local Python dependencies are missing, the page stays available and reports model loading/unavailable instead of inventing a review result.')

H('15. How to demonstrate it honestly')
B('<b>Start:</b> run <font name="DejaVuMono">bash start.sh</font> in the repository, then open <font name="DejaVuMono">http://127.0.0.1:8000</font> and wait for “Local Llama is ready.”')
B('<b>Show fixed settings:</b> point to AES-128-GCM, C++20 / Windows CNG and message tampering. Explain why a fixed profile makes the present evaluation tractable.')
B('<b>Paste a small AES CNG excerpt:</b> include a visible <font name="DejaVuMono">BCryptDecrypt</font> call whose status is discarded. Review it, click the cited line and show the F01–F05 list.')
B('<b>Show uncertainty:</b> submit a declaration-only excerpt or unrelated code and show “insufficient context” or “outside scope.” A model failure can also be shown as review unavailable.')
B('<b>Explain the boundary:</b> point to “candidate execution: not run” and state that the model is still a base model. Avoid describing the finding as a proved exploit.')
P('If asked for a “secure/not secure” answer: “Today the report gives source-review concerns and uncertainty. A confirmed pass/fail would require independent labels plus native CNG compilation and tamper tests on Windows.”')

H('16. Likely supervisor questions and concise answers')
T(['Question','Answer'],[
    ('Why GCM?','It combines encryption with authentication; the integration must handle nonce uniqueness, AAD, tag checking and failure status correctly.'),
    ('Why local Llama?','Submitted code stays in the local workflow and no paid API is required. The model can explain source concerns, but its opinions still need validation.'),
    ('Is the model trained?','The active model is the cached Llama-3.1-8B-Instruct base model. The 30-code AES candidate is prepared; training has not begun.'),
    ('Why only AES?','The current contract and five checks are fixed so data, prompts, UI and reports can be evaluated consistently. Multi-scheme work is historical/future scope.'),
    ('Can it prove code secure?','No. It checks source text and marks native execution not run. We need Windows CNG fixtures and independent evaluation for stronger claims.'),
    ('What is the next experiment?','Finish expert label review, obtain a fresh held-out AES set, measure baseline errors, train an adapter, then compare on untouched data.')],
    [56*mm,116*mm])

H('17. Next steps and success criteria')
P('First, review the full-session AES labels and build a fresh evaluation set by implementation family, including correct code, real misuse, suspicious-but-valid cases, incomplete context and out-of-scope code. Then measure base-model validity, per-check defect recall/precision, false positives, abstention, quoted-line accuracy and explanation quality. After the dataset is approved, run QLoRA locally and repeat the same evaluation. Only if the adapter improves relevant safety metrics should it be explicitly activated in the Python service. Separately, test Windows CNG code on a Windows machine with synthetic keys/messages and tampered ciphertext, nonce, tag and AAD. Keep source observations separate from confirmed runtime witnesses.')

H('18. File map and sources')
P('<b>Read first:</b> README.md, STATUS.md, docs/AES_REVIEW_CONTRACT.md. <b>Current code:</b> frontend/index.html, frontend/app.js, frontend/styles.css; backend/app.mjs, backend/verifier.mjs, backend/llm_client.mjs, backend/review_contract.mjs, backend/native_checks.mjs, backend/local_model.py; profiles/aes128_gcm_tampering.json; prompts/verify.txt; tools/start_local.mjs; start.sh/start.ps1. <b>Data:</b> training/aes_source_pilot_v1/data/manifest.json and train/validation/test.jsonl. <b>History:</b> phase1/, phase2/, phase3/, WALKTHROUGH.md, VALIDATION.md.')
P('<b>Primary API references:</b> <link href="https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptencrypt" color="#254fa0">Microsoft BCryptEncrypt</link>; <link href="https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptdecrypt" color="#254fa0">Microsoft BCryptDecrypt</link>; <link href="https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/ns-bcrypt-bcrypt_authenticated_cipher_mode_info" color="#254fa0">Microsoft authenticated-cipher parameters</link>. Model identification: <link href="https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct" color="#254fa0">Llama-3.1-8B-Instruct model card</link>. Project-specific claims above were checked against the local repository snapshot and dataset manifest.')

H('19. Quick glossary for the presentation')
T(['Term','Meaning in CryptAgent'],[
    ('AEAD','Authenticated encryption with associated data: encryption plus a tamper-detection tag.'),
    ('AAD','Data authenticated with a message but not encrypted, such as agreed metadata.'),
    ('Nonce','A per-encryption value that must not repeat under the same AES-GCM key.'),
    ('Tag','The authentication value checked during decryption; 16 bytes in this profile.'),
    ('CNG','Windows Cryptography Next Generation, the intended native cryptographic API.'),
    ('Inference','Running the already-loaded Llama model on submitted source; this is not training.'),
    ('QLoRA / LoRA','An efficient fine-tuning method that trains small adapter weights on a quantized base model; used experimentally here.'),
    ('Held-out set','Code examples excluded from training and reserved to measure behavior after training.'),
    ('Source observation','A deterministic text-pattern match that points to code for human inspection.'),
    ('Native witness','A future Windows CNG test result tied to an actual compiled candidate and input.')],
    [43*mm,129*mm])

H('20. Short command and status checklist')
C('cd /home/hp/Documents/Codex/2026-09-29/pull-and-setup/cryptAgent\nbash start.sh\n# Open http://127.0.0.1:8000 and wait for Local Llama is ready.\n# Automated contracts: npm test; python3 tests/test_local_model.py\n# Candidate dataset counts: training/aes_source_pilot_v1/data/manifest.json')
P('Before presenting, say explicitly: <b>“The local pipeline runs; the active base model is experimental; the 30-code candidate has not been used for training; submitted C++ has not been compiled or executed.”</b> This single statement prevents the historical tests, source observations and model opinions from being confused with a completed cryptographic verification.', 'Smallx')

class NumberedDoc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(str(filename), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                         topMargin=18*mm, bottomMargin=18*mm, title='CryptAgent presentation guide',
                         author='CryptAgent project')
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='normal')
        self.addPageTemplates(PageTemplate(id='guide', frames=frame, onPage=self.decorate))
    def decorate(self, canvas, doc):
        canvas.saveState()
        w,h=A4
        canvas.setStrokeColor(rule); canvas.line(18*mm,h-13*mm,w-18*mm,h-13*mm)
        canvas.setFont('DejaVu',7); canvas.setFillColor(muted)
        canvas.drawString(18*mm,h-11*mm,'CRYPTAGENT  •  PRESENTATION GUIDE')
        canvas.line(18*mm,14*mm,w-18*mm,14*mm)
        canvas.drawString(18*mm,10*mm,'Repository snapshot • 2 October 2026')
        canvas.drawRightString(w-18*mm,10*mm,f'Page {doc.page}')
        canvas.restoreState()

OUT.parent.mkdir(parents=True, exist_ok=True)
NumberedDoc(OUT).build(story)
print(OUT)
