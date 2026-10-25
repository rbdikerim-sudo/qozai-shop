document.addEventListener('DOMContentLoaded', () => {
    loadCheckoutSummary();
});

// Закрытие модального окна с предупреждением
function closeInfoModal() {
    const modal = document.getElementById('infoModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Функция красивого всплывающего уведомления (Toast)
function showToast(message, type = 'success') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

function loadCheckoutSummary() {
    let cart = JSON.parse(localStorage.getItem('qozai_cart')) || [];
    let selectedItems = cart.filter(item => item.selected !== false);
    
    const container = document.getElementById('checkoutItemsList');
    let total = 0;

    if (!container) return;

    if (selectedItems.length === 0) {
        container.innerHTML = '<p style="color: red; font-size: 13px;">Вы не выбрали ни одного товара в корзине!</p>';
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) submitBtn.disabled = true;
        return;
    }

    let html = '';
    selectedItems.forEach(item => {
        total += Number(item.price);
        html += `
            <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #e2e8f0;">
                <img src="${item.image_url}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 6px;">
                <div style="font-size: 13px;">
                    <b style="display: block; color: #111827;">${item.name}</b>
                    <span style="color: #6b7280;">Цвет: ${item.selectedColor}, Размер: ${item.selectedSize}</span>
                    <div style="color: #113f23; font-weight: 600; margin-top: 2px;">${Number(item.price).toLocaleString()} ₸</div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    const totalPriceEl = document.getElementById('checkoutTotalPrice');
    if (totalPriceEl) totalPriceEl.innerText = total.toLocaleString() + ' ₸';
}

function submitOrder(event) {
    event.preventDefault();

    const whatsapp = document.getElementById('whatsapp').value.trim();
    const instagram = document.getElementById('instagram').value.trim();
    const telegram = document.getElementById('telegram').value.trim();

    if (!whatsapp && !instagram && !telegram) {
        showToast('Укажите хотя бы один контакт (WhatsApp, Instagram или Telegram)!', 'error');
        return;
    }

    const fileInput = document.getElementById('receiptFile');
    if (fileInput.files.length === 0) {
        showToast('Пожалуйста, загрузите чек об оплате в формате PDF!', 'error');
        return;
    }

    let cart = JSON.parse(localStorage.getItem('qozai_cart')) || [];
    let selectedItems = cart.filter(item => item.selected !== false);

    let formData = new FormData();
    formData.append('full_name', document.getElementById('fullName').value);
    formData.append('address', document.getElementById('address').value);
    formData.append('whatsapp', whatsapp);
    formData.append('instagram', instagram);
    formData.append('telegram', telegram);
    formData.append('cart_items', JSON.stringify(selectedItems));
    formData.append('receipt', fileInput.files[0]);

    const submitBtn = document.getElementById('submitBtn');
    submitBtn.innerText = 'Проверка и отправка...';
    submitBtn.disabled = true;

    fetch('/submit_order', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let remainingCart = cart.filter(item => item.selected === false);
            localStorage.setItem('qozai_cart', JSON.stringify(remainingCart));

            document.getElementById('orderForm').style.display = 'none';
            document.getElementById('successMessage').style.display = 'block';
            showToast('Заказ успешно отправлен продавцу!', 'success');
        } else {
            showToast('Ошибка: ' + data.error, 'error');
            submitBtn.innerText = 'Завершить покупку';
            submitBtn.disabled = false;
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        showToast('Произошла ошибка при отправке заказа.', 'error');
        submitBtn.innerText = 'Завершить покупку';
        submitBtn.disabled = false;
    });
}