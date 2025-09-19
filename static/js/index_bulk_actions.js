document.addEventListener('DOMContentLoaded', function() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const itemCheckboxes = document.querySelectorAll('.item-checkbox');

    // Common bulk action buttons (may not exist on all pages)
    const moveBtn = document.getElementById('moveBtn');
    const copyBtn = document.getElementById('copyBtn');
    const deleteBtn = document.getElementById('deleteBtn');
    const bulkRenameBtn = document.getElementById('bulkRenameBtn');

    // Recycle Bin specific buttons (may not exist on all pages)
    const restoreSelectedBtn = document.getElementById('restoreSelectedBtn');
    const permanentDeleteSelectedBtn = document.getElementById('permanentDeleteSelectedBtn');
    const clearCacheBtn = document.getElementById('clearCacheBtn');

    function toggleCommonBulkActionButtons() {
        const currentItemCheckboxes = document.querySelectorAll('.item-checkbox');
        const anyChecked = Array.from(currentItemCheckboxes).some(c => c.checked);
        if (moveBtn) moveBtn.disabled = !anyChecked;
        if (copyBtn) copyBtn.disabled = !anyChecked;
        if (deleteBtn) deleteBtn.disabled = !anyChecked;
        if (bulkRenameBtn) bulkRenameBtn.disabled = !anyChecked;

    }

    function toggleRecycleBinButtons() {
        const currentItemCheckboxes = document.querySelectorAll('.item-checkbox');
        const hasChecked = Array.from(currentItemCheckboxes).some(cb => cb.checked);
        if (restoreSelectedBtn) restoreSelectedBtn.disabled = !hasChecked;
        if (permanentDeleteSelectedBtn) permanentDeleteSelectedBtn.disabled = !hasChecked;
    }

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function(e) {
            const currentItemCheckboxes = document.querySelectorAll('.item-checkbox');
            currentItemCheckboxes.forEach(checkbox => {
                checkbox.checked = e.target.checked;
            });
            toggleCommonBulkActionButtons();
            toggleRecycleBinButtons(); // Update recycle bin buttons too
        });
    }

    // Re-evaluate itemCheckboxes on DOM changes (e.g., search results loading)
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' || mutation.type === 'subtree') {
                // Re-attach event listeners to new checkboxes
                document.querySelectorAll('.item-checkbox').forEach(checkbox => {
                    if (!checkbox._hasClickListener) { // Prevent adding multiple listeners
                        checkbox.addEventListener('change', function() {
                            toggleCommonBulkActionButtons();
                            toggleRecycleBinButtons();
                        });
                        checkbox._hasClickListener = true;
                    }
                });
                toggleCommonBulkActionButtons();
                toggleRecycleBinButtons();
            }
        });
    });

    // Observe the table body for changes (where items are rendered)
    const tableBody = document.querySelector('table tbody');
    if (tableBody) {
        observer.observe(tableBody, { childList: true, subtree: true });
    }

    // Initial setup for existing checkboxes
    itemCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            toggleCommonBulkActionButtons();
            toggleRecycleBinButtons(); // Update recycle bin buttons too
        });
    });

    // Modals (common)
    const moveModal = document.getElementById('moveModal');
    if (moveModal) {
        moveModal.addEventListener('show.bs.modal', function (event) {
            const selectedItems = Array.from(itemCheckboxes)
                .filter(c => c.checked)
                .map(c => ({
                    id: c.dataset.itemId,
                    type: c.dataset.itemType
                }));
            document.getElementById('moveItems').value = JSON.stringify(selectedItems);
        });
    }

    const copyModal = document.getElementById('copyModal');
    if (copyModal) {
        copyModal.addEventListener('show.bs.modal', function (event) {
            const selectedItems = Array.from(itemCheckboxes)
                .filter(c => c.checked)
                .map(c => ({
                    id: c.dataset.itemId,
                    type: c.dataset.itemType
                }));
            document.getElementById('copyItems').value = JSON.stringify(selectedItems);
        });
    }

    const deleteModal = document.getElementById('deleteModal');
    if (deleteModal) {
        deleteModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const itemType = button.getAttribute('data-item-type');
            const itemIdOrPath = button.getAttribute('data-item-id');

            const modalTitle = deleteModal.querySelector('.modal-title');
            const deleteItemTypeInput = deleteModal.querySelector('#deleteItemType');
            const deleteItemIdOrPathInput = deleteModal.querySelector('#deleteItemIdOrPath');

            if (button.id === 'deleteBtn') { // Bulk delete
                const selectedItems = Array.from(itemCheckboxes)
                    .filter(c => c.checked)
                    .map(c => ({
                        id: c.dataset.itemId,
                        type: c.dataset.itemType
                    }));
                modalTitle.textContent = 'Move ' + selectedItems.length + ' item(s) to Recycle Bin';
                deleteItemIdOrPathInput.value = JSON.stringify(selectedItems);
                deleteItemTypeInput.value = 'bulk'; // Set type for backend
            } else { // Single delete
                modalTitle.textContent = 'Move ' + itemType + ' to Recycle Bin';
                deleteItemTypeInput.value = itemType;
                deleteItemIdOrPathInput.value = itemIdOrPath;
            }
        });
    }

    const renameModal = document.getElementById('renameModal');
    if (renameModal) {
        const renameTab = new bootstrap.Tab(document.getElementById('rename-new-name-tab'));
        renameModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const itemType = button.getAttribute('data-item-type');
            const oldName = button.getAttribute('data-old-name') || button.getAttribute('data-item-name');
            const itemId = button.getAttribute('data-item-id');

            const modalTitle = renameModal.querySelector('.modal-title');
            const newItemNameInput = renameModal.querySelector('#newItemName');
            const renameItemTypeInput = renameModal.querySelector('#renameItemType');
            const renameOldNameInput = renameModal.querySelector('#renameOldName');
            const renameItemIdInput = renameModal.querySelector('#renameItemId');
            const renameMethodInput = renameModal.querySelector('#renameMethod');

            modalTitle.textContent = 'Rename ' + itemType;
            newItemNameInput.value = oldName;
            renameItemTypeInput.value = itemType;
            renameOldNameInput.value = oldName;
            renameItemIdInput.value = itemId;

            // Reset to default tab and clear other inputs
            renameTab.show();
            renameModal.querySelector('#renameTemplate').value = '';
            renameModal.querySelector('#findString').value = '';
            renameModal.querySelector('#replaceString').value = '';
            renameMethodInput.value = 'new_name';
        });

        // Update renameMethod hidden input based on active tab
        renameModal.querySelectorAll('.nav-link').forEach(tabButton => {
            tabButton.addEventListener('shown.bs.tab', function (event) {
                const activeTabId = event.target.id;
                if (activeTabId === 'rename-new-name-tab') {
                    renameModal.querySelector('#renameMethod').value = 'new_name';
                } else if (activeTabId === 'rename-template-tab') {
                    renameModal.querySelector('#renameMethod').value = 'template';
                } else if (activeTabId === 'rename-find-replace-tab') {
                    renameModal.querySelector('#renameMethod').value = 'find_replace';
                }
            });
        });
    }

    const bulkRenameModal = document.getElementById('bulkRenameModal');
    if (bulkRenameModal) {
        const bulkRenameTab = new bootstrap.Tab(document.getElementById('bulk-rename-new-name-tab'));
        bulkRenameModal.addEventListener('show.bs.modal', function (event) {
            const selectedItems = Array.from(itemCheckboxes)
                .filter(c => c.checked)
                .map(c => ({
                    id: c.dataset.itemId,
                    type: c.dataset.itemType,
                    name: c.dataset.itemName // Pass item name for template/find-replace
                }));
            document.getElementById('bulkRenameItems').value = JSON.stringify(selectedItems);
            bulkRenameModal.querySelector('.modal-title').textContent = 'Rename ' + selectedItems.length + ' Item(s)';

            // Reset to default tab and clear other inputs
            bulkRenameTab.show();
            bulkRenameModal.querySelector('#bulkNewItemName').value = '';
            bulkRenameModal.querySelector('#bulkRenameTemplate').value = '';
            bulkRenameModal.querySelector('#bulkFindString').value = '';
            bulkRenameModal.querySelector('#bulkReplaceString').value = '';
            bulkRenameModal.querySelector('#bulkRenameMethod').value = 'new_name';
        });

        // Update renameMethod hidden input based on active tab
        bulkRenameModal.querySelectorAll('.nav-link').forEach(tabButton => {
            tabButton.addEventListener('shown.bs.tab', function (event) {
                const activeTabId = event.target.id;
                if (activeTabId === 'bulk-rename-new-name-tab') {
                    bulkRenameModal.querySelector('#bulkRenameMethod').value = 'new_name';
                } else if (activeTabId === 'bulk-rename-template-tab') {
                    bulkRenameModal.querySelector('#bulkRenameMethod').value = 'template';
                } else if (activeTabId === 'bulk-rename-find-replace-tab') {
                    bulkRenameModal.querySelector('#bulkRenameMethod').value = 'find_replace';
                }
            });
        });
    }



    // Recycle Bin specific actions
    if (restoreSelectedBtn && permanentDeleteSelectedBtn) {
        function createAndSubmitForm(actionUrl, confirmationMessage) {
            if (confirm(confirmationMessage)) {
                const selectedItems = Array.from(itemCheckboxes)
                    .filter(cb => cb.checked)
                    .map(cb => ({
                        id: parseInt(cb.value),
                        type: cb.dataset.itemType
                    }));
                
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = actionUrl;

                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'item_ids';
                input.value = JSON.stringify(selectedItems);
                form.appendChild(input);

                document.body.appendChild(form);
                form.submit();
            }
        }

        restoreSelectedBtn.addEventListener('click', function(event) {
            event.preventDefault();
            // Need to get url_for from Jinja2 context, so this part needs to be handled carefully.
            // For now, I'll use a placeholder and assume the Flask app will provide the correct URL.
            createAndSubmitForm("/restore_items", 'Are you sure you want to restore the selected items?');
        });

        permanentDeleteSelectedBtn.addEventListener('click', function(event) {
            event.preventDefault();
            // Same as above, placeholder for url_for
            createAndSubmitForm("/permanent_delete_items", 'Are you sure you want to permanently delete the selected items? This action cannot be undone.');
        });

        toggleRecycleBinButtons(); // Initial state for recycle bin buttons
    }

    // Initial state for common buttons
    toggleCommonBulkActionButtons();

    // Download Modal
    const downloadModal = document.getElementById('downloadModal');
    if (downloadModal) {
        let currentFileId = null;

        downloadModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            currentFileId = button.dataset.telegramFileId;
            const cachedLink = document.getElementById('downloadCachedLink');
            const directLink = document.getElementById('downloadDirectLink');
            cachedLink.href = `/download/${currentFileId}`;
            directLink.href = `/download/stream_nocache/${currentFileId}`;
        });

        const downloadToServerOnlyBtn = document.getElementById('downloadToServerOnlyBtn');
        if (downloadToServerOnlyBtn) {
            downloadToServerOnlyBtn.addEventListener('click', function() {
                if (currentFileId) {
                    fetch(`/cache_file/${currentFileId}`, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert(data.message); // Reverted to alert
                            } else {
                                alert('Error: ' + data.message); // Reverted to alert
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            alert('An unexpected error occurred.'); // Reverted to alert
                        });
                    const myModal = bootstrap.Modal.getInstance(downloadModal);
                    myModal.hide();
                }
            });
        }
    }

    // Bulk download to server
    const bulkDownloadBtn = document.getElementById('bulkDownloadToServerBtn');
    if (bulkDownloadBtn) {
        bulkDownloadBtn.addEventListener('click', async function() {
            const checkboxes = document.querySelectorAll('.item-checkbox:checked');
            const fileIds = Array.from(checkboxes)
                .filter(cb => cb.dataset.itemType === 'file')
                .map(cb => cb.dataset.telegramFileId);

            if (fileIds.length === 0) {
                alert('Please select at least one file to download.'); // Reverted to alert
                return;
            }

            const myModal = bootstrap.Modal.getInstance(document.getElementById('copyLinksModal'));
            myModal.hide();

            alert(`Starting background download for ${fileIds.length} files.`); // Reverted to alert

            for (const fileId of fileIds) {
                try {
                    const response = await fetch(`/cache_file/${fileId}`, { method: 'POST' });
                    const data = await response.json();
                    if (!data.success) {
                        alert(`Failed to start download for file ID: ${fileId}.`); // Reverted to alert
                    }
                } catch (error) {
                    console.error('Error starting download for file ID:', fileId, error);
                    alert(`An error occurred for file ID: ${fileId}.`); // Reverted to alert
                }
                // Small delay between requests to avoid overwhelming the server
                await new Promise(resolve => setTimeout(resolve, 200));
            }
        });
    }

    // Clear Cache Button (single item)
    document.querySelectorAll('.clear-cache-btn').forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            const itemType = this.dataset.itemType;

            if (confirm(`Are you sure you want to clear the cache for this ${itemType}?`)) {
                const itemsToClear = [{
                    id: itemId,
                    type: itemType
                }];

                fetch('/admin/clear_items_cache', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ items: itemsToClear }),
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                    } else {
                        alert('Failed to clear cache: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('Error clearing cache:', error);
                    alert('An error occurred while clearing cache.');
                });
            }
        });
    });

    if (clearCacheBtn) {
        clearCacheBtn.addEventListener('click', function() {
            const selectedItems = Array.from(document.querySelectorAll('.item-checkbox:checked'))
                .map(c => ({
                    id: c.dataset.itemId,
                    type: c.dataset.itemType
                }));

            if (selectedItems.length === 0) {
                alert('No items selected.');
                return;
            }

            if (confirm(`Are you sure you want to clear the cache for ${selectedItems.length} selected items?`)) {
                fetch('/admin/clear_items_cache', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ items: selectedItems }),
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                    } else {
                        alert('Failed to clear cache: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('Error clearing cache:', error);
                    alert('An error occurred while clearing cache.');
                });
            }
        });
    }
});