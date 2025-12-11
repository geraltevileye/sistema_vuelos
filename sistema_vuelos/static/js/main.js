// JavaScript para el Sistema de Vuelos

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar tooltips de Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Inicializar popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-ocultar alertas después de 5 segundos
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Confirmación para acciones de eliminación
    var deleteForms = document.querySelectorAll('form[action*="eliminar"], form[action*="cancelar"]');
    deleteForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!confirm('¿Está seguro de realizar esta acción? Esta acción no se puede deshacer.')) {
                e.preventDefault();
            }
        });
    });
    
    // Formatear números automáticamente
    var numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            if (this.value) {
                this.value = parseFloat(this.value).toFixed(2);
            }
        });
    });
    
    // Auto-completar fechas
    var dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        if (!input.value) {
            var today = new Date().toISOString().split('T')[0];
            input.value = today;
        }
    });
    
    // Validación de formularios
    var forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            var requiredFields = form.querySelectorAll('[required]');
            var isValid = true;
            
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('Por favor, complete todos los campos obligatorios.');
            }
        });
    });
    
    // Actualizar hora actual en el footer
    function updateCurrentTime() {
        var now = new Date();
        var timeString = now.toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        });
        var dateString = now.toLocaleDateString('es-ES', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        
        var timeElement = document.getElementById('current-time');
        if (timeElement) {
            timeElement.textContent = timeString + ' - ' + dateString;
        }
    }
    
    // Agregar elemento de tiempo al footer si no existe
    var footer = document.querySelector('.footer .text-muted');
    if (footer) {
        var timeSpan = document.createElement('span');
        timeSpan.id = 'current-time';
        timeSpan.className = 'd-block small';
        footer.appendChild(timeSpan);
        updateCurrentTime();
        setInterval(updateCurrentTime, 1000);
    }
    
    // Mejorar la experiencia en formularios de búsqueda
    var searchInputs = document.querySelectorAll('input[type="search"], input[name*="busqueda"]');
    searchInputs.forEach(function(input) {
        var clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'btn btn-outline-secondary btn-sm position-absolute end-0 top-50 translate-middle-y me-2 d-none';
        clearBtn.innerHTML = '×';
        clearBtn.style.zIndex = '5';
        
        var parent = input.parentElement;
        parent.style.position = 'relative';
        parent.appendChild(clearBtn);
        
        input.addEventListener('input', function() {
            if (this.value) {
                clearBtn.classList.remove('d-none');
            } else {
                clearBtn.classList.add('d-none');
            }
        });
        
        clearBtn.addEventListener('click', function() {
            input.value = '';
            clearBtn.classList.add('d-none');
            input.focus();
            
            // Si el formulario tiene un botón de submit, enviarlo automáticamente
            var form = input.closest('form');
            if (form) {
                form.submit();
            }
        });
    });
    
    // Agregar animación a los botones
    var buttons = document.querySelectorAll('.btn:not(.btn-link)');
    buttons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!this.classList.contains('disabled')) {
                this.classList.add('btn-active');
                setTimeout(() => {
                    this.classList.remove('btn-active');
                }, 300);
            }
        });
    });
});

// Función para exportar tablas a CSV
function exportTableToCSV(tableId, filename) {
    var table = document.getElementById(tableId);
    if (!table) return;
    
    var rows = table.querySelectorAll('tr');
    var csv = [];
    
    for (var i = 0; i < rows.length; i++) {
        var row = [], cols = rows[i].querySelectorAll('td, th');
        
        for (var j = 0; j < cols.length; j++) {
            // Limpiar el texto
            var text = cols[j].innerText.replace(/(\r\n|\n|\r)/gm, '').replace(/(\s\s)/gm, ' ');
            row.push('"' + text + '"');
        }
        
        csv.push(row.join(','));
    }
    
    var csvFile = new Blob([csv.join('\n')], { type: 'text/csv' });
    var downloadLink = document.createElement('a');
    downloadLink.download = filename || 'export.csv';
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

// Función para formatear números con separadores de miles
function formatNumber(number) {
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// Función para formatear fechas
function formatDate(dateString) {
    var date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Función para mostrar carga
function showLoading() {
    var loadingDiv = document.createElement('div');
    loadingDiv.id = 'loading-overlay';
    loadingDiv.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    `;
    loadingDiv.innerHTML = `
        <div class="spinner-border text-light" role="status">
            <span class="visually-hidden">Cargando...</span>
        </div>
    `;
    document.body.appendChild(loadingDiv);
}

// Función para ocultar carga
function hideLoading() {
    var loadingDiv = document.getElementById('loading-overlay');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// Interceptar envíos de formularios para mostrar carga
document.addEventListener('submit', function(e) {
    var form = e.target;
    if (form.method.toLowerCase() === 'post' && !form.classList.contains('no-loading')) {
        showLoading();
    }
});

// Interceptar clicks en enlaces que puedan llevar a acciones lentas
document.addEventListener('click', function(e) {
    var target = e.target;
    var link = target.closest('a');
    
    if (link && link.href && !link.target && !link.classList.contains('no-loading')) {
        // Verificar si es una acción que podría ser lenta
        var href = link.href.toLowerCase();
        if (href.includes('eliminar') || href.includes('exportar') || href.includes('generar')) {
            showLoading();
        }
    }
});
