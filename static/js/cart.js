document.addEventListener('DOMContentLoaded', () => {
    renderCart();
    updateCartBadge();
});

function getCart() {
    return JSON.parse(localStorage.getItem('qozai_cart')) || [];
}

function saveCart(cart) {
    localStorage.setItem('qozai_cart', JSON.stringify(cart));
}

function renderCart() {
    const cart = getCart();
    const container = document.getElementById('cartItemsList');
    
    if (!container) return;

    if (cart.length === 0) {
        container.innerHTML = `
            <div class="empty-cart">
                <p>Ваша корзина пока пуста.</p>
                <a href="/" class="btn-save" style="display:inline-block; margin-top:15px; text-decoration:none; text-align:center;">Вернуться к покупкам</a>
            </div>
        `;
        document.getElementById('selectedCount').innerText = '0 шт.';
        document.getElementById('totalPrice').innerText = '0 ₸';
        return;
    }

    let html = '';
    cart.forEach((item, index) => {
        const isChecked = item.selected !== false ? 'checked' : '';
        html += `
            <div class="cart-item">
                <input type="checkbox" class="item-checkbox" data-index="${index}" ${isChecked} onchange="toggleItemSelection(${index})">
                <img src="${item.image_url}" alt="${item.name}">
                <div class="cart-item-info">
                    <h4>${item.name}</h4>
                    <p><b>Код:</b> ${item.code} | <b>Категория:</b> ${item.category}</p>
                    <p><b>Цвет:</b> ${item.selectedColor || 'Стандарт'} | <b>Размер:</b> ${item.selectedSize || 'Uni'}</p>
                    <p class="price">${Number(item.price).toLocaleString()} ₸</p>
                </div>
                <button class="btn-remove-item" onclick="removeItem(${index})">Удалить</button>
            </div>
        `;
    });

    container.innerHTML = html;
    calculateTotal();
}

function toggleItemSelection(index) {
    let cart = getCart();
    cart[index].selected = !cart[index].selected;
    saveCart(cart);
    calculateTotal();
}

function removeItem(index) {
    let cart = getCart();
    cart.splice(index, 1);
    saveCart(cart);
    renderCart();
    updateCartBadge();
}

function calculateTotal() {
    let cart = getCart();
    let total = 0;
    let count = 0;

    cart.forEach(item => {
        if (item.selected !== false) {
            total += Number(item.price);
            count += 1;
        }
    });

    const selectedCountEl = document.getElementById('selectedCount');
    const totalPriceEl = document.getElementById('totalPrice');
    if (selectedCountEl) selectedCountEl.innerText = count + ' шт.';
    if (totalPriceEl) totalPriceEl.innerText = total.toLocaleString() + ' ₸';
}

function proceedToCheckout() {
    let cart = getCart();
    let selectedItems = cart.filter(item => item.selected !== false);
    
    if (selectedItems.length === 0) {
        alert('Пожалуйста, выберите хотя бы один товар для покупки!');
        return;
    }
    
    window.location.href = '/checkout';
}

function updateCartBadge() {
    let cart = getCart();
    const badge = document.getElementById('cartCount');
    if (badge) {
        badge.innerText = cart.length;
    }
}
