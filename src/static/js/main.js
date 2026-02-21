const setupProductFilters = () => {
	const list = document.querySelector('[data-products-list]');
	if (!list) {
		return;
	}

	const items = Array.from(list.querySelectorAll('[data-product-item]'));
	const searchInput = document.querySelector('[data-filter="search"]');
	const priceMinInput = document.querySelector('[data-filter="price-min"]');
	const priceMaxInput = document.querySelector('[data-filter="price-max"]');
	const offerToggle = document.querySelector('[data-filter="offer"]');
	const count = document.querySelector('[data-products-count]');

	const applyFilters = () => {
		const search = (searchInput?.value || '').trim().toLowerCase();
		const minPrice = Number(priceMinInput?.value || 0);
		const maxPriceValue = priceMaxInput?.value;
		const maxPrice = maxPriceValue ? Number(maxPriceValue) : null;
		const offersOnly = Boolean(offerToggle?.checked);

		const visibleItems = items.filter((item) => {
			const matchesSearch = !search || item.dataset.search.includes(search);
			const price = Number(item.dataset.price);
			const matchesMin = !Number.isFinite(minPrice) || price >= minPrice;
			const matchesMax = maxPrice === null || (!Number.isNaN(maxPrice) && price <= maxPrice);
			const matchesOffer = !offersOnly || (item.dataset.offer || '').trim() === 'on';
			return matchesSearch && matchesMin && matchesMax && matchesOffer;
		});

		const sortedItems = visibleItems.slice();
		sortedItems.sort((a, b) => Number(b.dataset.price) - Number(a.dataset.price));

		items.forEach((item) => {
			const isVisible = visibleItems.includes(item);
			item.style.display = isVisible ? '' : 'none';
		});

		sortedItems.forEach((item) => {
			list.appendChild(item);
		});

		if (count) {
			count.textContent = `Mostrando ${visibleItems.length} de ${items.length} productos`;
		}
	};

	[searchInput, priceMinInput, priceMaxInput, offerToggle].forEach((control) => {
		if (control) {
			control.addEventListener('input', applyFilters);
			control.addEventListener('change', applyFilters);
		}
	});

	applyFilters();
};

document.addEventListener('DOMContentLoaded', setupProductFilters);

const setupCartActions = () => {
	const buttons = Array.from(document.querySelectorAll('[data-product-id]'));
	if (!buttons.length) {
		return;
	}

	const cartCount = document.querySelector('[data-cart-count]');

	const updateCount = (count) => {
		if (!cartCount) {
			return;
		}
		cartCount.textContent = String(count);
	};

	buttons.forEach((button) => {
		button.addEventListener('click', async () => {
			const productId = button.dataset.productId;
			if (!productId) {
				return;
			}

			try {
				const response = await fetch('/cart/add', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
					},
					body: JSON.stringify({ product_id: productId, quantity: 1 }),
				});
				if (!response.ok) {
					return;
				}
				const data = await response.json();
				if (data && typeof data.cart_count === 'number') {
					updateCount(data.cart_count);
				}
			} catch (error) {
				console.error('Cart error', error);
			}
		});
	});
};

document.addEventListener('DOMContentLoaded', setupCartActions);

const setupCartPage = () => {
	const cartPage = document.querySelector('[data-cart-page]');
	if (!cartPage) {
		return;
	}

	const subtotalEl = cartPage.querySelector('[data-cart-subtotal]');
	const totalEl = cartPage.querySelector('[data-cart-total]');
	const cartCount = document.querySelector('[data-cart-count]');

	const updateSummary = (subtotal) => {
		if (subtotalEl) {
			subtotalEl.textContent = `$${subtotal}`;
		}
		if (totalEl) {
			totalEl.textContent = `$${subtotal}`;
		}
	};

	const updateCartCount = (count) => {
		if (cartCount) {
			cartCount.textContent = String(count);
		}
	};

	const syncItem = (itemEl, itemData) => {
		const lineTotalEl = itemEl.querySelector('[data-line-total]');
		if (lineTotalEl && itemData) {
			lineTotalEl.textContent = `$${itemData.line_total}`;
		}
	};

	const updateCart = async (productId, quantity, itemEl) => {
		try {
			const response = await fetch('/cart/update', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ product_id: productId, quantity }),
			});
			if (!response.ok) {
				return;
			}
			const data = await response.json();
			if (!data || data.status !== 'ok') {
				return;
			}
			updateCartCount(data.cart_count);
			updateSummary(data.subtotal);
			const itemData = data.items ? data.items[productId] : null;
			if (!itemData) {
				itemEl.remove();
			} else {
				syncItem(itemEl, itemData);
			}
		} catch (error) {
			console.error('Cart update error', error);
		}
	};

	const removeItem = async (productId, itemEl) => {
		try {
			const response = await fetch('/cart/remove', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ product_id: productId }),
			});
			if (!response.ok) {
				return;
			}
			const data = await response.json();
			if (!data || data.status !== 'ok') {
				return;
			}
			itemEl.remove();
			updateCartCount(data.cart_count);
			updateSummary(data.subtotal);
			if (!data.cart_count) {
				window.location.reload();
			}
		} catch (error) {
			console.error('Cart remove error', error);
		}
	};

	cartPage.querySelectorAll('[data-cart-item]').forEach((itemEl) => {
		const productId = itemEl.dataset.productId;
		const qtyInput = itemEl.querySelector('[data-cart-qty]');
		const removeBtn = itemEl.querySelector('[data-cart-remove]');
		const decreaseBtn = itemEl.querySelector('[data-qty-action="decrease"]');
		const increaseBtn = itemEl.querySelector('[data-qty-action="increase"]');

		if (qtyInput) {
			qtyInput.addEventListener('change', () => {
				const qty = Number(qtyInput.value || 1);
				updateCart(productId, qty, itemEl);
			});
		}

		if (decreaseBtn) {
			decreaseBtn.addEventListener('click', () => {
				const current = Number(qtyInput.value || 1);
				const next = Math.max(1, current - 1);
				qtyInput.value = next;
				updateCart(productId, next, itemEl);
			});
		}

		if (increaseBtn) {
			increaseBtn.addEventListener('click', () => {
				const current = Number(qtyInput.value || 1);
				const next = current + 1;
				qtyInput.value = next;
				updateCart(productId, next, itemEl);
			});
		}

		if (removeBtn) {
			removeBtn.addEventListener('click', () => {
				removeItem(productId, itemEl);
			});
		}
	});
};

document.addEventListener('DOMContentLoaded', setupCartPage);
