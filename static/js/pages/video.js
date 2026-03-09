function updateVideoLikeButton(videoId, liked, likeCount, animate = false) {
    const button = document.querySelector(`[data-video-id="${videoId}"]`);
    if (!button) return;

    const icon = button.querySelector('i');
    const count = button.querySelector('.like-count');

    if (icon) {
        icon.classList.toggle('bi-heart', !liked);
        icon.classList.toggle('bi-heart-fill', liked);

        if (animate && liked) {
            icon.classList.add('heart-liked');
            window.setTimeout(() => {
                icon.classList.remove('heart-liked');
            }, 400);
        }
    }

    if (count) {
        count.textContent = likeCount;
    }
}

async function toggleVideoLike(videoId, animate = false) {
    try {
        const response = await fetch(`/video/${videoId}/like`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (data.success) {
            updateVideoLikeButton(videoId, data.liked, data.like_count, animate);

            if (animate && navigator.vibrate && data.liked) {
                navigator.vibrate(50);
            }
        }
    } catch (error) {
        console.error('Errore like:', error);
    }
}

function bindVideoLikeButtons(options = {}) {
    const { animate = false } = options;

    document.querySelectorAll('.video-like-btn').forEach((button) => {
        if (button.dataset.spaBound) return;
        button.dataset.spaBound = 'true';
        button.addEventListener('click', function () {
            const videoId = this.dataset.videoId;
            if (!videoId) return;
            toggleVideoLike(videoId, animate);
        });
    });
}

window.initVideoList = function () {
    bindVideoLikeButtons({ animate: true });

    document.querySelectorAll('.confirm-delete-video').forEach((form) => {
        if (form.dataset.spaBound) return;
        form.dataset.spaBound = 'true';
        form.addEventListener('submit', function (event) {
            const message = this.dataset.confirmMessage || 'Eliminare questo video?';
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });
};

window.initVideoComments = function () {
    bindVideoLikeButtons({ animate: false });

    const replyToId = document.getElementById('replyToId');
    const replyToName = document.getElementById('replyToName');
    const replyToPreview = document.getElementById('replyToPreview');
    const replyPreview = document.getElementById('replyPreview');
    const commentInput = document.getElementById('commentInput');

    function clearReplyState() {
        if (replyToId) replyToId.value = '';
        if (replyPreview) replyPreview.classList.add('d-none');
        if (commentInput) {
            commentInput.placeholder = 'Scrivi un commento...';
        }
    }

    document.querySelectorAll('.set-reply-btn').forEach((button) => {
        if (button.dataset.spaBound) return;
        button.dataset.spaBound = 'true';
        button.addEventListener('click', function () {
            if (replyToId) replyToId.value = this.dataset.commentId || '';
            if (replyToName) replyToName.textContent = this.dataset.replyUserName || '';
            if (replyToPreview) replyToPreview.textContent = `${this.dataset.replyPreview || ''}...`;
            if (replyPreview) replyPreview.classList.remove('d-none');
            if (commentInput) {
                commentInput.placeholder = `Rispondi a ${this.dataset.replyUserName || ''}...`;
                commentInput.focus();
            }
        });
    });

    const clearReplyBtn = document.getElementById('clearReplyBtn');
    if (clearReplyBtn && !clearReplyBtn.dataset.spaBound) {
        clearReplyBtn.dataset.spaBound = 'true';
        clearReplyBtn.addEventListener('click', clearReplyState);
    }

    document.querySelectorAll('.confirm-delete-comment').forEach((form) => {
        if (form.dataset.spaBound) return;
        form.dataset.spaBound = 'true';
        form.addEventListener('submit', function (event) {
            const message = this.dataset.confirmMessage || 'Eliminare commento?';
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });
};