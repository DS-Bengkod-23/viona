<!doctype html>
<html lang="id">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Exploratory Data Analysis (EDA)</title>
    @vite(['resources/css/app.css', 'resources/js/app.js'])
</head>
<body>
    <div id="app" class="lms-app">
        <aside class="course-sidebar" data-sidebar>
            <div class="course-title">
                <h1>Exploratory Data Analysis (EDA)</h1>
            </div>
            <nav class="course-nav" id="course-nav" aria-label="Daftar materi">
                <div class="loading-menu">Memuat materi...</div>
            </nav>
            <button class="sidebar-toggle" type="button" data-toggle-sidebar aria-label="Sembunyikan sidebar">
                &laquo;
            </button>
        </aside>

        <main class="lesson-shell">
            <header class="lesson-topbar">
                <button class="mobile-menu" type="button" data-toggle-sidebar aria-label="Buka daftar materi">
                    <span></span>
                    <span></span>
                    <span></span>
                </button>
                <div>
                    <p class="eyebrow">Bengkel Koding LMS</p>
                    <h2 id="lesson-heading">Exploratory Data Analysis (EDA)</h2>
                </div>
                <div class="progress-pill" id="progress-pill">0% selesai</div>
            </header>

            <section class="lesson-card" id="lesson-content">
                <div class="empty-state">
                    <div class="loader"></div>
                    <p>Menyiapkan salinan materi dari HAR...</p>
                </div>
            </section>

            <footer class="lesson-actions">
                <button class="secondary-btn" type="button" id="prev-lesson">Sebelumnya</button>
                <button class="primary-btn" type="button" id="complete-lesson">Tandai Selesai</button>
                <button class="secondary-btn" type="button" id="next-lesson">Berikutnya</button>
            </footer>
        </main>
    </div>

    <!-- Viona AI Assistant Widget -->
    <iframe id="viona-widget" src="/dashboard/widget"
            {{-- autoplay WAJIB: TTS Cartesia diputar lewat <audio> di dalam iframe ini.
                 Tanpa izin ini audio.play() ditolak browser dan widget diam-diam
                 jatuh ke Web Speech. (SpeechSynthesis tidak terkena aturan autoplay,
                 jadi gejalanya terlihat seperti "Cartesia tidak aktif".) --}}
            allow="microphone; autoplay"
            style="position:fixed; bottom:0; right:0; width:210px; height:220px; border:none; z-index:9999; background:transparent; transition: all 0.3s ease;">
    </iframe>
    <script>
        // Kirim konteks materi ke widget Viona. Di halaman KUIS, sengaja TIDAK
        // mengirim isi materi (agar Viona tak pernah "melihat" soal) — cukup flag
        // isQuiz + judul course (dinamis, mendukung course apa pun tanpa hardcode).
        function postVionaContext(widget) {
            if (!widget || !widget.contentWindow) return;
            const lc = document.getElementById('lesson-content');
            const isQuiz = !!(lc && lc.querySelector('.quiz-card'));
            const course = window.__vionaCourse || {};
            const courseEl = document.querySelector('.course-title h1');
            widget.contentWindow.postMessage({
                type: 'viona-context',
                // Kirim SELURUH isi course (tanpa quiz). TIDAK dikosongkan saat halaman
                // quiz — Viona tetap perlu materi untuk bantu KONSEP; flag isQuiz hanya
                // memicu guard "jangan beri jawaban soal" di backend.
                text: course.text || (lc && lc.innerText) || '',
                isQuiz: isQuiz,
                courseTitle: course.title || (courseEl && courseEl.innerText) || document.title || '',
            }, '*');
        }

        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'viona-resize') {
                const widget = document.getElementById('viona-widget');
                if (event.data.isOpen) {
                    widget.style.width = '780px';
                    widget.style.height = '630px';
                    postVionaContext(widget);
                } else {
                    widget.style.width = '210px';
                    widget.style.height = '220px';
                }
            }
        });

        // ── Text Selection to Ask Viona ──
        document.addEventListener('DOMContentLoaded', function() {
            // Create the floating button
            const vionaBtn = document.createElement('button');
            vionaBtn.id = 'viona-highlight-btn';
            vionaBtn.innerHTML = '✨ Tanya Viona';
            vionaBtn.style.cssText = `
                display: none;
                position: absolute;
                background-color: #7c3aed;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                z-index: 10000;
                transition: opacity 0.2s ease-in-out;
                opacity: 0;
            `;
            document.body.appendChild(vionaBtn);

            let selectedText = "";

            document.addEventListener('mouseup', function(e) {
                // If clicking inside the button itself, don't hide
                if (e.target === vionaBtn) return;

                const selection = window.getSelection();
                const text = selection.toString().trim();

                if (text.length > 0) {
                    selectedText = text;
                    const range = selection.getRangeAt(0);
                    const rect = range.getBoundingClientRect();
                    
                    // Position button slightly above the selection
                    vionaBtn.style.top = (rect.top + window.scrollY - 40) + 'px';
                    vionaBtn.style.left = (rect.left + window.scrollX + (rect.width / 2) - 50) + 'px';
                    vionaBtn.style.display = 'block';
                    
                    // Fade in effect
                    setTimeout(() => {
                        vionaBtn.style.opacity = '1';
                    }, 10);
                } else {
                    hideButton();
                }
            });

            // Hide button if selection is cleared via keyboard or other means
            document.addEventListener('selectionchange', function() {
                const selection = window.getSelection();
                if (selection.toString().trim().length === 0) {
                    hideButton();
                }
            });

            function hideButton() {
                vionaBtn.style.opacity = '0';
                setTimeout(() => {
                    if (vionaBtn.style.opacity === '0') {
                        vionaBtn.style.display = 'none';
                    }
                }, 200);
            }

            vionaBtn.addEventListener('mousedown', function(e) {
                // Prevent browser from clearing text selection when clicking the button
                e.preventDefault();
            });

            vionaBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation(); // Prevent closing selection
                
                const widget = document.getElementById('viona-widget');
                if (widget && widget.contentWindow) {
                    // Update context explicitly before sending quote
                    postVionaContext(widget);
                    widget.contentWindow.postMessage({
                        type: 'viona-quote',
                        text: selectedText
                    }, '*');
                }
                hideButton();
                window.getSelection().removeAllRanges(); // Clear selection after click
            });
            
            // Observe lesson content changes to update Viona's context dynamically
            const lessonContent = document.getElementById('lesson-content');
            if (lessonContent) {
                const observer = new MutationObserver(function(mutations) {
                    postVionaContext(document.getElementById('viona-widget'));
                });
                observer.observe(lessonContent, { childList: true, subtree: true, characterData: true });
            }
        });
    </script>
</body>
</html>
