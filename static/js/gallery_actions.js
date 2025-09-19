document.addEventListener('DOMContentLoaded', function () {
    var galleryActionModal = document.getElementById('galleryActionModal');
    if (galleryActionModal) {
        galleryActionModal.addEventListener('show.bs.modal', function (event) {
            // Button that triggered the modal
            var triggerElement = event.relatedTarget;

            // Extract info from data-* attributes
            var previewUrl = triggerElement.getAttribute('data-preview-url');
            var telegramLink = triggerElement.getAttribute('data-telegram-link');

            // Get the buttons inside the modal
            var previewButton = galleryActionModal.querySelector('#galleryActionPreview');
            var telegramButton = galleryActionModal.querySelector('#galleryActionTelegram');

            if (previewButton) {
                previewButton.href = previewUrl;
            }

            if (telegramButton) {
                if (telegramLink && telegramLink !== 'None') {
                    telegramButton.href = telegramLink;
                    telegramButton.style.display = 'inline-block';
                } else {
                    telegramButton.style.display = 'none';
                }
            }
        });
    }
});
