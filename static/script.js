document.addEventListener("DOMContentLoaded", function () {
    console.log("Script running...");

    const places = window.placesData || [];

    const map = L.map('map').setView([20, 0], 2);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // Add markers only if places exist
    if (places.length === 0) {
        console.warn("No places found.");
        return;
    }

    places.forEach(place => {
        L.marker([place.lat, place.lng])
            .addTo(map)
            .bindPopup(place.name);
    });
});


