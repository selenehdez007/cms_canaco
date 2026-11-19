(function () {
    const form = document.getElementById('category-form');
    if (!form) return;

    const input = document.getElementById('category-name');
    const submitButton = document.getElementById('category-submit');
    const cancelWrap = document.getElementById('category-cancel-wrap');
    const cancelButton = document.getElementById('category-cancel');
    const tableBody = document.getElementById('category-table-body');
    const feedback = document.getElementById('category-feedback');
    let editingRow = null;

    function showFeedback(message, isError) {
        feedback.textContent = message;
        feedback.className = `alert alert-${isError ? 'danger' : 'success'}`;
    }

    function clearFeedback() {
        feedback.textContent = '';
        feedback.className = 'alert d-none';
    }

    function updateRowNumbers() {
        tableBody.querySelectorAll('[data-category-id]').forEach((row, index) => {
            row.querySelector('.category-number').textContent = index + 1;
        });
    }

    function makeCell(className, value) {
        const cell = document.createElement('td');
        cell.className = className;
        cell.textContent = value;
        return cell;
    }

    function makeCategoryRow(category) {
        const row = document.createElement('tr');
        row.dataset.categoryId = category.id;
        row.dataset.editUrl = category.edit_url;
        row.dataset.deleteUrl = category.delete_url;
        row.appendChild(makeCell('category-number', ''));
        row.appendChild(makeCell('category-name', category.nombre));
        row.appendChild(makeCell('category-user', category.usuario));
        row.appendChild(makeCell('category-date', category.fecha));

        const editCell = document.createElement('td');
        const editButton = document.createElement('button');
        editButton.type = 'button';
        editButton.className = 'btn btn-info btn-sm category-edit';
        editButton.textContent = 'Editar';
        editCell.appendChild(editButton);
        row.appendChild(editCell);

        const deleteCell = document.createElement('td');
        const deleteButton = document.createElement('button');
        deleteButton.type = 'button';
        deleteButton.className = 'btn btn-danger btn-sm category-delete';
        deleteButton.textContent = 'Eliminar';
        deleteCell.appendChild(deleteButton);
        row.appendChild(deleteCell);
        return row;
    }

    function leaveEditMode() {
        editingRow = null;
        input.value = '';
        form.action = form.dataset.createUrl;
        submitButton.textContent = 'Agregar';
        cancelWrap.classList.add('d-none');
    }

    async function sendRequest(url, body) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: body
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.message || 'No se pudo completar la operación.');
        }
        return data;
    }

    form.addEventListener('submit', async function (event) {
        event.preventDefault();
        clearFeedback();
        try {
            const result = await sendRequest(form.action, new FormData(form));
            const category = result.categoria;
            if (editingRow) {
                editingRow.querySelector('.category-name').textContent = category.nombre;
            } else {
                const emptyRow = tableBody.querySelector('[data-empty-row]');
                if (emptyRow) emptyRow.remove();
                tableBody.appendChild(makeCategoryRow(category));
            }
            updateRowNumbers();
            leaveEditMode();
            showFeedback(result.message, false);
        } catch (error) {
            showFeedback(error.message, true);
        }
    });

    cancelButton.addEventListener('click', function () {
        leaveEditMode();
        clearFeedback();
    });

    tableBody.addEventListener('click', async function (event) {
        const editButton = event.target.closest('.category-edit');
        if (editButton) {
            editingRow = editButton.closest('[data-category-id]');
            input.value = editingRow.querySelector('.category-name').textContent;
            form.action = editingRow.dataset.editUrl;
            submitButton.textContent = 'Actualizar';
            cancelWrap.classList.remove('d-none');
            clearFeedback();
            input.focus();
            return;
        }

        const deleteButton = event.target.closest('.category-delete');
        if (!deleteButton) return;

        const row = deleteButton.closest('[data-category-id]');
        clearFeedback();
        try {
            const result = await sendRequest(row.dataset.deleteUrl, new FormData(form));
            row.remove();
            if (editingRow === row) leaveEditMode();
            if (!tableBody.querySelector('[data-category-id]')) {
                const emptyRow = document.createElement('tr');
                emptyRow.dataset.emptyRow = '';
                const cell = document.createElement('td');
                cell.colSpan = 6;
                cell.className = 'text-center';
                cell.textContent = 'No hay categorías aún.';
                emptyRow.appendChild(cell);
                tableBody.appendChild(emptyRow);
            }
            updateRowNumbers();
            showFeedback(result.message, false);
        } catch (error) {
            showFeedback(error.message, true);
        }
    });
})();
