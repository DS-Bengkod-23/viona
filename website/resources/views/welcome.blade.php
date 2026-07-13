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
            style="position:fixed; bottom:0; right:0; width:100px; height:100px; border:none; z-index:9999; background:transparent; transition: all 0.3s ease;">
    </iframe>
    <script>
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'viona-resize') {
                const widget = document.getElementById('viona-widget');
                if (event.data.isOpen) {
                    widget.style.width = '420px';
                    widget.style.height = '600px';
                } else {
                    widget.style.width = '100px';
                    widget.style.height = '100px';
                }
            }
        });
    </script>
</body>
</html>
