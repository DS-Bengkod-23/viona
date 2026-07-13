import './bootstrap';

const app = document.querySelector('#app');
const nav = document.querySelector('#course-nav');
const content = document.querySelector('#lesson-content');
const heading = document.querySelector('#lesson-heading');
const progressPill = document.querySelector('#progress-pill');
const prevButton = document.querySelector('#prev-lesson');
const nextButton = document.querySelector('#next-lesson');
const completeButton = document.querySelector('#complete-lesson');
const toggleButtons = document.querySelectorAll('[data-toggle-sidebar]');

const state = {
    data: null,
    flatLessons: [],
    activeId: null,
    completed: new Set(JSON.parse(localStorage.getItem('lms-completed-lessons') || '[]')),
};

const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

const stripTags = (value) => String(value ?? '').replace(/<[^>]+>/g, '');

function saveProgress() {
    localStorage.setItem('lms-completed-lessons', JSON.stringify([...state.completed]));
}

function normalizeItem(raw) {
    if (!raw) {
        return null;
    }

    return {
        ...raw,
        id: Number(raw.id),
        builder_fields: raw.builder_fields || [],
    };
}

function itemFromRef(ref) {
    const item = normalizeItem(state.data.items[String(ref.id)]);
    if (item) {
        return item;
    }

    return normalizeItem({
        id: ref.id,
        type: 'sub-section',
        title: ref.title || 'Materi belum terekam',
        item_type: ref.item_type || 'ARTICLE',
        sort_order: 999,
        unavailable: ref.unavailable,
        builder_fields: [],
    });
}

function sectionTotals(section) {
    let total = 0;
    let done = 0;

    for (const ref of section.items) {
        total += 1;
        if (state.completed.has(Number(ref.id))) {
            done += 1;
        }

        for (const childId of ref.children || []) {
            total += 1;
            if (state.completed.has(Number(childId))) {
                done += 1;
            }
        }
    }

    return { total, done };
}

function flattenLessons() {
    state.flatLessons = [];

    for (const section of state.data.sections) {
        for (const ref of section.items) {
            state.flatLessons.push({ id: Number(ref.id), section: section.id });

            for (const childId of ref.children || []) {
                state.flatLessons.push({ id: Number(childId), section: section.id, parent: Number(ref.id) });
            }
        }
    }
}

function renderNav() {
    nav.innerHTML = state.data.sections.map((section) => {
        const totals = sectionTotals(section);

        const rows = section.items.map((ref) => {
            const item = itemFromRef(ref);
            const children = ref.children || [];
            const isDone = state.completed.has(item.id);
            const isActive = item.id === state.activeId;
            const childDone = children.filter((id) => state.completed.has(Number(id))).length;

            const parentRow = `
                <button class="lesson-row ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}" type="button" data-lesson-id="${item.id}">
                    <span class="lesson-dot" aria-hidden="true"></span>
                    <span class="lesson-name">${escapeHtml(item.title)}</span>
                    ${children.length ? `<span class="lesson-count">${childDone}/${children.length}</span><span class="row-arrow"></span>` : ''}
                </button>
            `;

            const childRows = children.map((childId) => {
                const child = itemFromRef({ id: childId });
                const childDoneClass = state.completed.has(child.id) ? 'done' : '';
                const childActiveClass = child.id === state.activeId ? 'active' : '';

                return `
                    <button class="lesson-row child ${childDoneClass} ${childActiveClass}" type="button" data-lesson-id="${child.id}">
                        <span class="lesson-dot" aria-hidden="true"></span>
                        <span class="lesson-name">${escapeHtml(child.title)}</span>
                    </button>
                `;
            }).join('');

            return parentRow + childRows;
        }).join('');

        return `
            <section class="section-block" data-section="${section.id}">
                <button class="section-heading" type="button" data-section-toggle="${section.id}">
                    <span>${escapeHtml(section.title)}</span>
                    <span class="chevron" aria-hidden="true"></span>
                </button>
                <div class="lesson-list">${rows}</div>
            </section>
        `;
    }).join('');

    nav.querySelectorAll('[data-lesson-id]').forEach((button) => {
        button.addEventListener('click', () => setActiveLesson(Number(button.dataset.lessonId)));
    });

    nav.querySelectorAll('[data-section-toggle]').forEach((button) => {
        button.addEventListener('click', () => {
            button.closest('.section-block').classList.toggle('is-closed');
        });
    });
}

function markdownTable(lines, index) {
    if (index + 1 >= lines.length || !/^\s*\|?\s*:?-{3,}/.test(lines[index + 1])) {
        return null;
    }

    const rows = [];
    let cursor = index;

    while (cursor < lines.length && lines[cursor].includes('|')) {
        rows.push(lines[cursor]);
        cursor += 1;
    }

    const cells = (line) => line
        .trim()
        .replace(/^\|/, '')
        .replace(/\|$/, '')
        .split('|')
        .map((cell) => inlineMarkdown(cell.trim()));

    const head = cells(rows[0]).map((cell) => `<th>${cell}</th>`).join('');
    const body = rows.slice(2).map((row) => `<tr>${cells(row).map((cell) => `<td>${cell}</td>`).join('')}</tr>`).join('');

    return {
        html: `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`,
        next: cursor,
    };
}

function inlineMarkdown(value) {
    return escapeHtml(value)
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>');
}

function markdownToHtml(markdown) {
    const lines = String(markdown ?? '').replace(/\r\n/g, '\n').split('\n');
    const html = [];
    let paragraph = [];
    let list = null;
    let inCode = false;
    let code = [];

    const flushParagraph = () => {
        if (!paragraph.length) {
            return;
        }

        html.push(`<p>${inlineMarkdown(paragraph.join(' '))}</p>`);
        paragraph = [];
    };

    const closeList = () => {
        if (!list) {
            return;
        }

        html.push(`</${list}>`);
        list = null;
    };

    for (let i = 0; i < lines.length; i += 1) {
        const raw = lines[i];
        const line = raw.trim();

        if (line.startsWith('```')) {
            if (inCode) {
                html.push(`<pre><code>${escapeHtml(code.join('\n'))}</code></pre>`);
                code = [];
                inCode = false;
            } else {
                flushParagraph();
                closeList();
                inCode = true;
            }
            continue;
        }

        if (inCode) {
            code.push(raw);
            continue;
        }

        if (!line) {
            flushParagraph();
            closeList();
            continue;
        }

        const table = markdownTable(lines, i);
        if (table) {
            flushParagraph();
            closeList();
            html.push(table.html);
            i = table.next - 1;
            continue;
        }

        const headingMatch = line.match(/^(#{2,5})\s+(.+)$/);
        if (headingMatch) {
            flushParagraph();
            closeList();
            const level = Math.min(4, headingMatch[1].length);
            html.push(`<h${level}>${inlineMarkdown(headingMatch[2])}</h${level}>`);
            continue;
        }

        const quoteMatch = line.match(/^>\s+(.+)$/);
        if (quoteMatch) {
            flushParagraph();
            closeList();
            html.push(`<blockquote>${inlineMarkdown(quoteMatch[1])}</blockquote>`);
            continue;
        }

        const bulletMatch = line.match(/^[-*]\s+(.+)$/);
        if (bulletMatch) {
            flushParagraph();
            if (list !== 'ul') {
                closeList();
                list = 'ul';
                html.push('<ul>');
            }
            html.push(`<li>${inlineMarkdown(bulletMatch[1])}</li>`);
            continue;
        }

        const orderedMatch = line.match(/^\d+\.\s+(.+)$/);
        if (orderedMatch) {
            flushParagraph();
            if (list !== 'ol') {
                closeList();
                list = 'ol';
                html.push('<ol>');
            }
            html.push(`<li>${inlineMarkdown(orderedMatch[1])}</li>`);
            continue;
        }

        paragraph.push(line);
    }

    flushParagraph();
    closeList();

    return html.join('');
}

function contentAsHtml(value) {
    const text = String(value ?? '').trim();
    if (!text) {
        return '';
    }

    if (/<[a-z][\s\S]*>/i.test(text)) {
        return text;
    }

    return markdownToHtml(text);
}

function youtubeEmbed(url) {
    const value = String(url ?? '');
    const shortMatch = value.match(/youtu\.be\/([^?&]+)/);
    const longMatch = value.match(/[?&]v=([^?&]+)/);
    const embedMatch = value.match(/embed\/([^?&]+)/);
    const id = shortMatch?.[1] || longMatch?.[1] || embedMatch?.[1];

    if (!id) {
        return '';
    }

    return `https://www.youtube.com/embed/${id}`;
}

function assetUrl(url) {
    return state.data.assetMap?.[url] || url;
}

function renderField(field, index) {
    if (field.type === 'richtext') {
        return `<div class="content-block rich-content">${contentAsHtml(field.content)}</div>`;
    }

    if (field.type === 'image') {
        return `
            <figure class="content-block">
                <img class="field-image" src="${escapeHtml(assetUrl(field.content))}" alt="Ilustrasi materi ${index + 1}">
            </figure>
        `;
    }

    if (field.type === 'video') {
        const embed = youtubeEmbed(field.content);
        return embed
            ? `<iframe class="content-block video-frame" src="${escapeHtml(embed)}" title="Video materi" allowfullscreen></iframe>`
            : '';
    }

    return '';
}

function renderQuiz(item) {
    const questions = item.builder_fields || [];

    if (!questions.length) {
        return '<p class="rich-content">Pertanyaan kuis ini tidak ikut terekam di HAR.</p>';
    }

    return `
        <div class="quiz-list">
            ${questions.map((field, questionIndex) => {
                const inputType = field.type === 'multiple' ? 'checkbox' : 'radio';
                const options = field.options || [];
                const optionHtml = options.length
                    ? options.map((option, optionIndex) => `
                        <label class="option-row">
                            <input type="${inputType}" name="quiz-${field.id}" value="${optionIndex}">
                            <span>${escapeHtml(option.text || option.content || option.label || option.option || '')}</span>
                        </label>
                    `).join('')
                    : `<textarea class="short-answer" placeholder="Tulis jawaban singkat"></textarea>`;

                return `
                    <article class="quiz-card">
                        <div class="quiz-question">${questionIndex + 1}. ${contentAsHtml(field.content)}</div>
                        ${optionHtml}
                        <span class="badge">${field.points || 0} poin</span>
                    </article>
                `;
            }).join('')}
        </div>
    `;
}

function renderLesson(item) {
    const isQuiz = item.item_type === 'QUIZ';
    const fields = item.builder_fields || [];
    const body = item.unavailable
        ? '<div class="rich-content"><p>Halaman ini muncul di navigasi HAR, tetapi payload API detailnya tidak ikut terekam. Slotnya tetap ditampilkan agar struktur course lengkap.</p></div>'
        : isQuiz
            ? renderQuiz(item)
            : fields.length
                ? fields.map(renderField).join('')
                : '<div class="rich-content"><p>Materi ini tercatat di struktur kursus, tetapi konten detailnya tidak ada dalam HAR.</p></div>';

    content.innerHTML = `
        <div class="lesson-meta">
            <span class="badge">${escapeHtml(item.item_type || 'ARTICLE')}</span>
            <span class="badge">ID ${item.id}</span>
        </div>
        <h1 class="lesson-title">${escapeHtml(item.title)}</h1>
        ${body}
    `;
}

function updateProgress() {
    const total = state.flatLessons.length || 1;
    const done = state.flatLessons.filter((lesson) => state.completed.has(lesson.id)).length;
    const percent = Math.round((done / total) * 100);
    progressPill.textContent = `${percent}% selesai`;
}

function setActiveLesson(id) {
    const item = itemFromRef({ id });
    if (!item) {
        return;
    }

    state.activeId = id;
    heading.textContent = item.title;
    renderLesson(item);
    renderNav();
    updateButtons();

    if (window.innerWidth <= 900) {
        app.classList.add('sidebar-collapsed');
    }

    history.replaceState(null, '', `/kursus/5/${item.type || 'sub-section'}/${id}`);
}

function updateButtons() {
    const index = state.flatLessons.findIndex((lesson) => lesson.id === state.activeId);
    const isDone = state.completed.has(state.activeId);

    prevButton.disabled = index <= 0;
    nextButton.disabled = index < 0 || index >= state.flatLessons.length - 1;
    completeButton.textContent = isDone ? 'Sudah Selesai' : 'Tandai Selesai';
}

function goToOffset(offset) {
    const index = state.flatLessons.findIndex((lesson) => lesson.id === state.activeId);
    const target = state.flatLessons[index + offset];

    if (target) {
        setActiveLesson(target.id);
    }
}

async function boot() {
    const response = await fetch('/data/course.json');
    state.data = await response.json();
    flattenLessons();

    const pathId = Number(location.pathname.match(/\/(\d+)$/)?.[1]);
    const firstId = state.flatLessons[0]?.id;
    const initialId = state.flatLessons.some((lesson) => lesson.id === pathId) ? pathId : firstId;

    app.classList.toggle('sidebar-collapsed', window.innerWidth <= 900);
    setActiveLesson(initialId);
    updateProgress();
}

toggleButtons.forEach((button) => {
    button.addEventListener('click', () => app.classList.toggle('sidebar-collapsed'));
});

prevButton.addEventListener('click', () => goToOffset(-1));
nextButton.addEventListener('click', () => goToOffset(1));
completeButton.addEventListener('click', () => {
    state.completed.add(state.activeId);
    saveProgress();
    renderNav();
    updateProgress();
    updateButtons();
});

boot().catch((error) => {
    content.innerHTML = `
        <div class="empty-state">
            <p>Gagal memuat data course.</p>
            <code>${escapeHtml(error.message)}</code>
        </div>
    `;
});
