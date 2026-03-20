document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    function getCsrfHeaders(extraHeaders = {}) {
        return csrfToken ? { ...extraHeaders, 'X-CSRFToken': csrfToken } : extraHeaders;
    }

    // ==========================================
    // SHARED UTILITIES
    // ==========================================
    const toastContainer = document.getElementById('toast-container');

    // Create container if missing (Main page might not have it in HTML)
    if (!toastContainer && document.body) {
        const div = document.createElement('div');
        div.id = 'toast-container';
        document.body.appendChild(div);
    }

    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        // Trigger reflow for animation
        void toast.offsetWidth;
        toast.classList.add('show');

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }

    // ==========================================
    // PAGE DETECTION
    // ==========================================
    const isMainPage = !!document.getElementById('slideshow-container');
    const isAdminPage = !!document.getElementById('drop-zone');

    // ==========================================
    // MAIN PAGE LOGIC (Slideshow & Chat)
    // ==========================================
    if (isMainPage) {
        initSlideshow();
        initChat();
    }

    function clampChannel(value, min = 0, max = 255) {
        return Math.max(min, Math.min(max, Math.round(value)));
    }

    function mixColor(base, target, weight) {
        return [
            clampChannel(base[0] * (1 - weight) + target[0] * weight),
            clampChannel(base[1] * (1 - weight) + target[1] * weight),
            clampChannel(base[2] * (1 - weight) + target[2] * weight)
        ];
    }

    function colorToCss(color) {
        return color.map(channel => clampChannel(channel)).join(', ');
    }

    function applyAmbientPanelTheme(sourceImage) {
        const root = document.documentElement;
        const activeStyle = root.getAttribute('data-home-style');
        if (!['style-2', 'style-4', 'style-5', 'style-6'].includes(activeStyle) || !sourceImage || !sourceImage.naturalWidth) {
            return;
        }

        try {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d', { willReadFrequently: true });
            if (!context) return;

            const sampleWidth = 40;
            const sampleHeight = 40;
            canvas.width = sampleWidth;
            canvas.height = sampleHeight;
            context.drawImage(sourceImage, 0, 0, sampleWidth, sampleHeight);

            const { data } = context.getImageData(0, 0, sampleWidth, sampleHeight);
            let totalWeight = 0;
            let avgR = 0;
            let avgG = 0;
            let avgB = 0;
            let brightestScore = -1;
            let darkestScore = 1000;
            let brightColor = [82, 119, 186];
            let darkColor = [26, 34, 46];

            for (let i = 0; i < data.length; i += 4) {
                const alpha = data[i + 3] / 255;
                if (alpha < 0.35) continue;

                const r = data[i];
                const g = data[i + 1];
                const b = data[i + 2];
                const luma = (r * 0.299) + (g * 0.587) + (b * 0.114);
                const saturation = Math.max(r, g, b) - Math.min(r, g, b);
                const weight = alpha * (0.8 + saturation / 255);

                avgR += r * weight;
                avgG += g * weight;
                avgB += b * weight;
                totalWeight += weight;

                if (luma > brightestScore) {
                    brightestScore = luma;
                    brightColor = [r, g, b];
                }
                if (luma < darkestScore) {
                    darkestScore = luma;
                    darkColor = [r, g, b];
                }
            }

            if (!totalWeight) return;

            const averageColor = [
                avgR / totalWeight,
                avgG / totalWeight,
                avgB / totalWeight
            ];

            const primary = mixColor(averageColor, [255, 255, 255], 0.12);
            const secondary = mixColor(brightColor, [120, 164, 220], 0.22);
            const tertiary = mixColor(darkColor, [12, 18, 28], 0.36);

            root.style.setProperty('--style2-panel-color-a', colorToCss(primary));
            root.style.setProperty('--style2-panel-color-b', colorToCss(secondary));
            root.style.setProperty('--style2-panel-color-c', colorToCss(tertiary));

            const glassA = mixColor(averageColor, [255, 214, 165], 0.16);
            const glassB = mixColor(brightColor, [255, 238, 192], 0.18);
            const glassC = mixColor(darkColor, [70, 110, 140], 0.28);

            root.style.setProperty('--style4-card-color-a', colorToCss(glassA));
            root.style.setProperty('--style4-card-color-b', colorToCss(glassB));
            root.style.setProperty('--style4-card-color-c', colorToCss(glassC));

            const edgeAccent = mixColor(brightColor, [120, 190, 225], 0.26);
            root.style.setProperty('--style5-accent', colorToCss(edgeAccent));

            const posterA = mixColor(averageColor, [245, 241, 236], 0.72);
            const posterB = mixColor(averageColor, [231, 234, 237], 0.58);
            const posterC = mixColor(brightColor, [201, 209, 218], 0.44);
            root.style.setProperty('--style6-surface-a', colorToCss(posterA));
            root.style.setProperty('--style6-surface-b', colorToCss(posterB));
            root.style.setProperty('--style6-surface-c', colorToCss(posterC));
        } catch (error) {
            console.warn('Ambient panel theme extraction failed:', error);
        }
    }

    function initSlideshow() {
        const container = document.getElementById('slideshow-container');
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');

        // History stack for "Previous" button
        // Store full image objects: {url: '...', date: '...'}
        let history = [];
        let currentPhoto = null; // Current photo object
        let slideshowInterval = null;
        const SLIDE_DURATION = 300000; // 5 Minutes
        let isNavigating = false; // Debounce flag for remote control

        // Preload cache: fetch the next photo in advance
        let preloadedPhoto = null;
        let preloadedImgEl = null; // Keep an Image() reference to hold browser cache

        // Start slideshow immediately using server logic
        nextImage();
        startSlideshowTimer();

        // Force Show Polling
        let isForceMode = false;
        let currentDisplayedUrl = null;

        setInterval(checkForceShow, 10000); // Check every 10s

        function checkForceShow() {
            fetch('/api/status', { credentials: 'same-origin' })
                .then(res => {
                    if (!res.ok) throw new Error('status auth/network error');
                    return res.json();
                })
                .then(data => {
                    const forceUrl = data.force_url;

                    if (forceUrl) {
                        if (currentDisplayedUrl !== forceUrl) {
                            console.log("Force inserting:", forceUrl);
                            isForceMode = true;
                            if (slideshowInterval) clearInterval(slideshowInterval);
                            nextImage();
                        }
                    } else {
                        if (isForceMode) {
                            isForceMode = false;
                            console.log("Resuming slideshow");
                            startSlideshowTimer();
                            nextImage();
                        }
                    }
                })
                .catch(err => console.error("Poll error", err));
        }

        // Functions
        function showImage(photoData, direction = 'next') {
            if (!photoData || !photoData.url) return;

            currentDisplayedUrl = photoData.url;

            const url = `/static/photos/${photoData.url}`;
            const date = photoData.date;

            // Create Slide Group (starts invisible, opacity:0 via CSS)
            const group = document.createElement('div');
            group.className = 'slide-group';

            // Background (Blurred) — hint GPU this will animate
            const bg = document.createElement('img');
            bg.className = 'slide-bg';
            bg.style.willChange = 'opacity';

            // Foreground (Contain)
            const fg = document.createElement('img');
            fg.className = 'slide';
            fg.onload = () => {
                const isPortrait = fg.naturalHeight > fg.naturalWidth;
                fg.classList.toggle('is-portrait', isPortrait);
                fg.classList.toggle('is-landscape', !isPortrait);
                group.classList.toggle('is-portrait', isPortrait);
                group.classList.toggle('is-landscape', !isPortrait);
                applyAmbientPanelTheme(fg);
            };
            fg.src = url;
            if (fg.complete && fg.naturalWidth > 0) {
                const isPortrait = fg.naturalHeight > fg.naturalWidth;
                fg.classList.toggle('is-portrait', isPortrait);
                fg.classList.toggle('is-landscape', !isPortrait);
                group.classList.toggle('is-portrait', isPortrait);
                group.classList.toggle('is-landscape', !isPortrait);
                applyAmbientPanelTheme(fg);
            }

            // Date Overlay
            if (date) {
                const dateEl = document.createElement('div');
                dateEl.className = 'slide-date';

                // Default date text
                let htmlContent = `拍摄于: ${date}`;

                // Baby Age Logic (Only if name matches or any tag exists if name is generic)
                const targetName = window.BABY_CONFIG.name || "宝宝";
                if (photoData.tags && (photoData.tags.indexOf(targetName) !== -1)) {
                    const ageText = getBabyAge(date);
                    if (ageText) {
                        htmlContent += `<br><span style="font-size: 0.9em; opacity: 0.9;">${ageText}</span>`;
                    }
                }

                dateEl.innerHTML = htmlContent;
                group.appendChild(dateEl);
            }

            group.appendChild(bg);
            group.appendChild(fg);

            // ── 深海打捞彩蛋：is_salvaged 视觉注入 ──────────────────────
            if (photoData.is_salvaged === true) {
                // 给前景图加复古滤镜（transition 由 CSS 控制，2s 平滑过渡）
                fg.classList.add('salvage-filter');

                // 动态创建「记忆偶然被打捞」浮字
                const salvageText = document.createElement('div');
                salvageText.className = 'salvage-text';
                salvageText.textContent = '记忆偶然被打捞';
                group.appendChild(salvageText);
            } else {
                // 常规照片：清除残留状态
                fg.classList.remove('salvage-filter');
                // salvage-text 随 group 新建，不会有残留，无需额外清除
            }
            // ──────────────────────────────────────────────────────────────

            container.appendChild(group);

            // ✅ Wait for background image to fully load before fading in
            // This prevents the "blank → blurry jump" artifact
            const triggerFadeIn = () => {
                requestAnimationFrame(() => {
                    group.classList.add('active');
                });
            };

            if (bg.complete && bg.naturalWidth > 0) {
                // Already cached by browser (e.g. preloaded)
                triggerFadeIn();
            } else {
                bg.onload = triggerFadeIn;
                bg.onerror = triggerFadeIn; // Fail gracefully
            }
            // Assign src after registering onload to avoid race condition
            bg.src = url;

            // Preload the next photo after a short delay so it doesn't compete
            // with the current transition's network/render budget
            setTimeout(preloadNext, 1500);

            // Clean up old slides — actively release image memory
            const allGroups = container.querySelectorAll('.slide-group');
            if (allGroups.length > 2) {
                for (let i = 0; i < allGroups.length - 2; i++) {
                    const oldGroup = allGroups[i];
                    const imgs = oldGroup.querySelectorAll('img');
                    imgs.forEach(img => { img.src = ''; img.removeAttribute('src'); });
                    oldGroup.remove();
                }
            }
            // Remove the second-to-last after transition completes
            if (allGroups.length >= 2) {
                const fadeOutGroup = allGroups[allGroups.length - 2];
                setTimeout(() => {
                    if (fadeOutGroup && fadeOutGroup.parentNode) {
                        const imgs = fadeOutGroup.querySelectorAll('img');
                        imgs.forEach(img => { img.src = ''; img.removeAttribute('src'); });
                        fadeOutGroup.remove();
                    }
                    isNavigating = false;
                }, 2500);
            } else {
                isNavigating = false;
            }

            const loading = document.getElementById('loading');
            if (loading) loading.remove();
        }

        // ✅ Preload next photo from server into browser cache
        function preloadNext() {
            fetch('/api/get_photo', { credentials: 'same-origin' })
                .then(res => {
                    if (!res.ok) throw new Error('Preload failed');
                    return res.json();
                })
                .then(photo => {
                    preloadedPhoto = photo;
                    // Pre-fetch both bg and fg into browser cache
                    const url = `/static/photos/${photo.url}`;
                    preloadedImgEl = new Image();
                    preloadedImgEl.src = url;
                })
                .catch(err => console.warn('Preload error (non-critical):', err));
        }

        // Get baby config from backend
        const BABY_CONFIG = window.BABY_CONFIG || { name: '', birthday: '' };

        function getBabyAge(dateStr) {
            if (!dateStr) return null;

            // Parse birthday from config (format: YYYY-MM-DD)
            const birthday = BABY_CONFIG.birthday;
            if (!birthday) return null;

            const birthParts = birthday.split('-');
            const birthYear = parseInt(birthParts[0], 10);
            const birthMonth = parseInt(birthParts[1], 10);
            const birthDay = parseInt(birthParts[2], 10);

            const photoParts = dateStr.split('-');
            const photoYear = parseInt(photoParts[0], 10);
            const photoMonth = parseInt(photoParts[1], 10);
            const photoDay = parseInt(photoParts[2], 10);

            if ([birthYear, birthMonth, birthDay, photoYear, photoMonth, photoDay].some(Number.isNaN)) {
                return null;
            }

            let ageYears = photoYear - birthYear;
            let ageMonths = photoMonth - birthMonth;
            let ageDays = photoDay - birthDay;

            if (ageDays < 0) {
                ageMonths--;
            }
            if (ageMonths < 0) {
                ageYears--;
                ageMonths += 12;
            }

            if (ageYears < 0) return null;

            let result = BABY_CONFIG.name || "宝宝 ";
            if (ageYears > 0) {
                result += `${ageYears} 岁`;
            }
            if (ageMonths > 0) {
                if (ageYears > 0) result += " ";
                result += `${ageMonths} 个月`;
            } else if (ageYears === 0 && ageMonths === 0) {
                return BABY_CONFIG.name ? `${BABY_CONFIG.name} 满月了` : "宝宝满月了";
            }
            return result + "了";
        }

        function nextImage() {
            // ✅ Use preloaded photo if available for instant display
            if (preloadedPhoto) {
                const photo = preloadedPhoto;
                preloadedPhoto = null;
                preloadedImgEl = null;
                if (currentPhoto) {
                    history.push(currentPhoto);
                    if (history.length > 50) history.shift();
                }
                currentPhoto = photo;
                showImage(photo, 'next');
                return;
            }

            // Fallback: fetch from server if no preloaded photo ready
            fetch('/api/get_photo', { credentials: 'same-origin' })
                .then(res => {
                    if (!res.ok) throw new Error('Failed to load photo');
                    return res.json();
                })
                .then(photo => {
                    if (currentPhoto) {
                        history.push(currentPhoto);
                        if (history.length > 50) history.shift();
                    }
                    currentPhoto = photo;
                    showImage(photo, 'next');
                })
                .catch(err => {
                    console.error("Slideshow error:", err);
                    isNavigating = false; // Fix: release the lock on error
                    setTimeout(nextImage, 10000);
                });
        }

        function prevImage() {
            if (history.length > 0) {
                // If we go back, the current photo is lost to future "next" logic (it will be random again)
                // But we can just pop from history.
                const photo = history.pop();
                currentPhoto = photo; // Update current
                showImage(photo, 'prev');
            } else {
                // Fallback if no history
                nextImage();
            }
        }

        function startSlideshowTimer() {
            if (slideshowInterval) clearInterval(slideshowInterval);
            slideshowInterval = setInterval(() => {
                nextImage();
            }, SLIDE_DURATION);
        }

        function resetTimer() {
            startSlideshowTimer();
        }

        // Event Listeners (Override inline onclicks logic)
        // Note: Inline onclick="prevImage()" expects global function. 
        // We will attach listeners directly to elements and expose globals as fallback.

        if (prevBtn) {
            prevBtn.onclick = (e) => {
                e.preventDefault();
                prevImage();
                resetTimer();
            };
        }
        if (nextBtn) {
            nextBtn.onclick = (e) => {
                e.preventDefault();
                nextImage();
                resetTimer();
            };
        }
        // Expose functions globally for Android TV remote control
        window.prevImage = function () {
            if (isNavigating) return;
            isNavigating = true;
            prevImage();
            resetTimer();
        };
        window.nextImage = function () {
            if (isNavigating) return;
            isNavigating = true;
            nextImage();
            resetTimer();
        };

        // Keyboard event listener for TV remote D-Pad keys (with debounce)
        document.addEventListener('keydown', function (e) {
            if (isNavigating) return; // Debounce: ignore if still transitioning
            switch (e.key) {
                case 'ArrowLeft':
                    isNavigating = true;
                    prevImage();
                    resetTimer();
                    e.preventDefault();
                    break;
                case 'ArrowRight':
                case 'Enter':
                    isNavigating = true;
                    nextImage();
                    resetTimer();
                    e.preventDefault();
                    break;
            }
        });
    }

    function initChat() {
        const messagesContainer = document.getElementById('chat-messages');
        const chatContainer = document.getElementById('chat-container');
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send-btn');
        let lastMessageId = null;

        // Fetch Messages
        function fetchMessages() {
            fetch('/api/messages?limit=50', { credentials: 'same-origin' })
                .then(res => {
                    if (!res.ok) throw new Error('messages auth/network error');
                    return res.json();
                })
                .then(data => {
                    renderMessages(data);
                })
                .catch(err => console.error('Chat error:', err));
        }

        function escapeHtml(str) {
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function renderMessages(messages) {
            // 只有当用户本来就在底部附近时，刷新后才自动吸附到底部；
            // 否则保留当前位置，避免用户向上翻历史留言时被强制拉回底部。
            const isNearBottom =
                chatContainer.scrollTop + chatContainer.clientHeight >= chatContainer.scrollHeight - 50;

            messagesContainer.innerHTML = '';

            messages.forEach(msg => {
                const row = document.createElement('div');
                row.className = `message-row ${msg.sender === CURRENT_USER ? 'my-message' : 'their-message'}`;

                // Show name for others
                let nameHtml = '';
                if (msg.sender !== CURRENT_USER) {
                    nameHtml = `<div class="sender-name">${escapeHtml(msg.sender)}</div>`;
                }

                row.innerHTML = `
                    ${nameHtml}
                    <div class="message-bubble">${escapeHtml(msg.content)}</div>
                `;
                messagesContainer.appendChild(row);
                lastMessageId = msg.id;
            });

            if (isNearBottom || messages.length <= 3) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }

        function sendMessage() {
            const content = input.value.trim();
            if (!content) return;

            fetch('/api/send', {
                method: 'POST',
                credentials: 'same-origin',
                headers: getCsrfHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({ content: content })
            })
                .then(res => {
                    if (!res.ok) throw new Error('send auth/network error');
                    return res.json();
                })
                .then(msg => {
                    input.value = '';
                    fetchMessages(); // Refresh immediately
                })
                .catch(err => {
                    console.error('Send error:', err);
                    showToast('发送失败', 'error');
                });
        }

        if (sendBtn) {
            sendBtn.addEventListener('click', sendMessage);
        }

        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });
        }

        // Poll for messages
        setInterval(fetchMessages, 30000);
        fetchMessages();
    }


    // ==========================================
    // ADMIN PAGE LOGIC
    // ==========================================
    if (isAdminPage) {
        initAdmin();
    }

    function initAdmin() {
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const previewArea = document.getElementById('upload-preview-area');
        const previewGrid = document.getElementById('preview-grid');
        const selectedCountSpan = document.getElementById('selected-count');
        const clearBtn = document.getElementById('clear-selection-btn');
        const uploadBtn = document.getElementById('upload-btn');
        const uploadForceBtn = document.getElementById('upload-force-btn');
        const progressContainer = document.getElementById('progress-container');
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');

        // Gallery
        const galleryGrid = document.getElementById('gallery-grid');
        const refreshBtn = document.getElementById('refresh-gallery-btn');

        let selectedFiles = [];

        // --- Upload Logic ---
        // dropZone is now a <label>, so click triggers input natively. 
        // No JS listener needed for click.

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
            fileInput.value = '';
        });

        function handleFiles(files) {
            const newFiles = Array.from(files).filter(file => file.type.startsWith('image/'));
            if (newFiles.length === 0) return;

            selectedFiles = [...selectedFiles, ...newFiles];
            updatePreviewUI();
        }

        function updatePreviewUI() {
            previewGrid.innerHTML = '';
            selectedCountSpan.textContent = `已选择 ${selectedFiles.length} 个文件`;

            if (selectedFiles.length > 0) {
                previewArea.classList.remove('hidden');
            } else {
                previewArea.classList.add('hidden');
                return;
            }

            selectedFiles.forEach((file, index) => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const card = document.createElement('div');
                    card.className = 'preview-card';
                    card.innerHTML = `
                        <div class="preview-image" style="background-image: url('${e.target.result}')"></div>
                        <div class="preview-info">
                            <span class="file-name">${file.name}</span>
                            <button class="remove-btn" data-index="${index}">&times;</button>
                        </div>
                    `;
                    card.querySelector('.remove-btn').addEventListener('click', (ev) => {
                        ev.stopPropagation();
                        removeFile(index);
                    });
                    previewGrid.appendChild(card);
                };
                reader.readAsDataURL(file);
            });
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updatePreviewUI();
        }

        clearBtn.addEventListener('click', () => {
            selectedFiles = [];
            updatePreviewUI();
        });

        uploadBtn.addEventListener('click', () => {
            if (selectedFiles.length === 0) {
                showToast('请先选择文件', 'error');
                return;
            }

            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file);
            });

            uploadBtn.disabled = true;
            uploadBtn.textContent = '上传中...';
            progressContainer.classList.remove('hidden');
            progressBar.style.width = '0%';
            progressText.textContent = '准备上传...';

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/upload', true);
            if (csrfToken) xhr.setRequestHeader('X-CSRFToken', csrfToken);

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    progressBar.style.width = percentComplete + '%';
                    progressText.textContent = `上传进度: ${Math.round(percentComplete)}%`;
                }
            };

            xhr.onload = function () {
                if (xhr.status === 200) {
                    showToast(`成功上传 ${selectedFiles.length} 张图片`, 'success');
                    selectedFiles = [];
                    updatePreviewUI();
                    loadGallery();
                } else {
                    showToast('上传失败: ' + xhr.statusText, 'error');
                }
                uploadBtn.disabled = false;
                uploadBtn.textContent = '开始上传';
                progressContainer.classList.add('hidden');
            };

            xhr.onerror = function () {
                showToast('网络错误', 'error');
                uploadBtn.disabled = false;
                uploadBtn.textContent = '开始上传';
                progressContainer.classList.add('hidden');
            };

            xhr.send(formData);
        });

        // Force Upload Logic
        if (uploadForceBtn) {
            uploadForceBtn.addEventListener('click', () => {
                if (selectedFiles.length === 0) {
                    showToast('请先选择文件', 'error');
                    return;
                }
                if (selectedFiles.length !== 1) {
                    showToast('“立即展示”功能仅支持单张照片', 'error');
                    return;
                }

                const formData = new FormData();
                formData.append('files', selectedFiles[0]);

                uploadForceBtn.disabled = true;
                uploadForceBtn.textContent = '处理中...';
                progressContainer.classList.remove('hidden');
                progressBar.style.width = '0%';
                progressText.textContent = '正在上传并设置优先展示...';

                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/upload?force=true', true);
                if (csrfToken) xhr.setRequestHeader('X-CSRFToken', csrfToken);

                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        progressBar.style.width = percentComplete + '%';
                        progressText.textContent = `上传进度: ${Math.round(percentComplete)}%`;
                    }
                };

                xhr.onload = function () {
                    if (xhr.status === 200) {
                        showToast(`已成功上传并将在几秒内展示`, 'success');
                        selectedFiles = [];
                        updatePreviewUI();
                        loadGallery();
                    } else {
                        showToast('上传失败 (可能非单张或服务器错误)', 'error');
                    }
                    uploadForceBtn.disabled = false;
                    uploadForceBtn.textContent = '上传并立即展示 (10分钟)';
                    progressContainer.classList.add('hidden');
                };

                xhr.onerror = function () {
                    showToast('网络错误', 'error');
                    uploadForceBtn.disabled = false;
                    uploadForceBtn.textContent = '上传并立即展示 (10分钟)';
                    progressContainer.classList.add('hidden');
                };

                xhr.send(formData);
            });
        }

        // --- Gallery Logic ---
        function loadGallery() {
            galleryGrid.innerHTML = '<div class="loading-spinner">正在加载照片库...</div>';

            fetch('/api/images', { credentials: 'same-origin' })
                .then(response => {
                    if (!response.ok) throw new Error('Network error');
                    const contentType = response.headers.get("content-type");
                    if (!contentType || !contentType.includes("application/json")) {
                        throw new TypeError("No JSON");
                    }
                    return response.json();
                })
                .then(data => {
                    // Update: data is now list of objects {url, date}
                    renderGallery(data);
                })
                .catch(error => {
                    console.error('Error loading gallery:', error);
                    galleryGrid.innerHTML = '<div class="error-msg">加载照片失败，请刷新重试</div>';
                });
        }

        function renderGallery(imageObjects) {
            galleryGrid.innerHTML = '';

            if (imageObjects.length === 0) {
                galleryGrid.innerHTML = '<div class="empty-state">相册是空的，快去上传吧！</div>';
                return;
            }

            imageObjects.forEach(img => {
                const card = document.createElement('div');
                card.className = 'gallery-card-item';
                const filename = img.url; // Relative path from backend
                const url = `/static/photos/${filename}`;
                const dateInfo = img.date ? `\n拍摄时间: ${img.date}` : '';

                card.innerHTML = `
                    <div class="gallery-image" style="background-image: url('${url}')" loading="lazy" title="${filename}${dateInfo}"></div>
                    <div class="gallery-overlay">
                        <button class="delete-btn" title="删除图片">
                            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 0 00-1 1v3M4 7h16"></path></svg>
                        </button>
                        <a href="${url}" target="_blank" class="view-btn" title="查看大图">
                        <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                        </a>
                    </div>
                `;

                card.querySelector('.delete-btn').addEventListener('click', () => {
                    if (confirm('确定要删除这张照片吗？')) {
                        deleteImage(filename, card);
                    }
                });

                galleryGrid.appendChild(card);
            });
        }

        function deleteImage(filename, cardElement) {
            fetch(`/api/images/${filename}`, {
                method: 'DELETE'
            })
                .then(response => {
                    if (response.ok) {
                        showToast('照片已删除', 'success');
                        cardElement.remove();
                        if (galleryGrid.children.length === 0) {
                            galleryGrid.innerHTML = '<div class="empty-state">相册是空的，快去上传吧！</div>';
                        }
                    } else {
                        showToast('删除失败', 'error');
                    }
                })
                .catch(error => {
                    console.error('Delete error:', error);
                    showToast('删除出错', 'error');
                });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', loadGallery);
        }

        loadGallery();
    }
});
