document.addEventListener('DOMContentLoaded', () => {
    updateCartBadge();
});

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

function showDetails(product) {
    const panel = document.getElementById('detailPanel');
    if (!panel) return;
    
    const colors = product.colors ? product.colors.split(',').map(c => c.trim()) : ['Стандарт'];
    const sizes = product.sizes_ru ? product.sizes_ru.split(',').map(s => s.trim()) : ['Uni'];

    panel.innerHTML = `
        <div class="detail-content">
            <img src="${product.image_url}" alt="${product.name}">
            <h3>${product.name}</h3>
            <p class="price" style="font-size: 18px; margin-bottom: 10px; color: #113f23;">${Number(product.price).toLocaleString()} ₸</p>
            <p><b>Код товара:</b> <span style="color: #0d9488; font-weight: 600;">${product.code}</span></p>
            <p><b>Категория:</b> ${product.category}</p>
            
            <div style="margin: 12px 0;">
                <label style="font-size:12px; font-weight:600; color: #6b7280; text-transform:uppercase;">Цвет:</label>
                <select id="selectedColor" style="width:100%; padding:8px; margin-top:4px; border-radius:6px; border:1px solid #e2e8f0; font-size:13px;">
                    ${colors.map(c => `<option value="${c}">${c}</option>`).join('')}
                </select>
            </div>

            <div style="margin: 12px 0;">
                <label style="font-size:12px; font-weight:600; color: #6b7280; text-transform:uppercase;">Размер (RU):</label>
                <select id="selectedSize" style="width:100%; padding:8px; margin-top:4px; border-radius:6px; border:1px solid #e2e8f0; font-size:13px;">
                    ${sizes.map(s => `<option value="${s}">${s}</option>`).join('')}
                </select>
            </div>

            <p style="margin-top: 10px;"><b>Состав:</b> ${product.composition}</p>
            <p><b>Рейтинг:</b> ⭐ ${product.rating} / 5.0</p>
            
            <button class="btn-save" style="margin-top: 15px;" onclick='addToCart(${JSON.stringify(product)})'>В корзину</button>
        </div>
    `;
}

function addToCart(product) {
    const colorSelect = document.getElementById('selectedColor');
    const sizeSelect = document.getElementById('selectedSize');
    
    product.selectedColor = colorSelect ? colorSelect.value : 'Стандарт';
    product.selectedSize = sizeSelect ? sizeSelect.value : 'Uni';
    product.selected = true;

    let cart = JSON.parse(localStorage.getItem('qozai_cart')) || [];
    cart.push(product);
    localStorage.setItem('qozai_cart', JSON.stringify(cart));

    updateCartBadge();
    
    // Вместо стандартного alert выводим красивое уведомление
    showToast('Товар успешно добавлен в корзину!', 'success');
}

function updateCartBadge() {
    let cart = JSON.parse(localStorage.getItem('qozai_cart')) || [];
    const badge = document.getElementById('cartCount');
    if (badge) {
        badge.innerText = cart.length;
    }
}