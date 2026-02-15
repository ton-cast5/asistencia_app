// static/js/script.js
async function escanearQR() {
    // Usar instascan o html5-qrcode
    const scanner = new Html5QrcodeScanner('reader', { 
        fps: 10, 
        qrbox: { width: 250, height: 250 } 
    });
    
    scanner.render(async (decodedText) => {
        try {
            const qrData = JSON.parse(decodedText);
            
            // Obtener ubicación actual
            navigator.geolocation.getCurrentPosition(async (position) => {
                const latitud = position.coords.latitude;
                const longitud = position.coords.longitude;
                
                // Enviar al servidor
                const response = await fetch('/registrar_asistencia', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        clase_id: qrData.clase_id,
                        latitud: latitud,
                        longitud: longitud,
                        telefono_id: localStorage.getItem('telefono_id')
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('✅ Asistencia registrada');
                } else {
                    alert('❌ ' + result.message);
                }
            });
        } catch (error) {
            alert('QR inválido');
        }
    });
}

// Login automático por dispositivo
window.onload = () => {
    const telefono_id = localStorage.getItem('telefono_id');
    if (!telefono_id) {
        // Generar ID único del dispositivo
        const newId = 'device_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('telefono_id', newId);
    }
    
    // Intentar login automático
    fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telefono_id: localStorage.getItem('telefono_id') })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            window.location.href = data.rol === 'profesor' ? '/dashboard_profesor' : '/dashboard_alumno';
        }
    });
};