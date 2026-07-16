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
            allow="microphone"
            style="position:fixed; bottom:0; right:0; width:210px; height:220px; border:none; z-index:9999; background:transparent; transition: all 0.3s ease;">
    </iframe>
    <script>
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'viona-resize') {
                const widget = document.getElementById('viona-widget');
                if (event.data.isOpen) {
                    widget.style.width = '560px';
                    widget.style.height = '630px';
                    
                    // Inject Context: Send lesson content to Viona Widget
                    const lessonContent = document.getElementById('lesson-content');
                    if (lessonContent && widget.contentWindow) {
                        // Extract text, replacing multiple newlines with single spaces to keep it clean
                        const text = lessonContent.innerText || "";
                        widget.contentWindow.postMessage({ 
                            type: 'viona-context', 
                            text: text 
                        }, '*');
                    }
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
                    const lessonContent = document.getElementById('lesson-content');
                    if (lessonContent) {
                        widget.contentWindow.postMessage({ 
                            type: 'viona-context', 
                            text: lessonContent.innerText || "" 
                        }, '*');
                    }
                    
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
                    const widget = document.getElementById('viona-widget');
                    if (widget && widget.contentWindow) {
                        widget.contentWindow.postMessage({ 
                            type: 'viona-context', 
                            text: lessonContent.innerText || "" 
                        }, '*');
                    }
                });
                observer.observe(lessonContent, { childList: true, subtree: true, characterData: true });
            }
        });
    </script>
</body>
</html>
