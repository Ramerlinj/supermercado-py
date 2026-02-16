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