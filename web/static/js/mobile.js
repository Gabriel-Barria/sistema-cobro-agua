/**
 * Mobile.js - JavaScript para Interfaz Mobile de Lecturas
 * Maneja: menú hamburguesa, modales, AJAX, validaciones
 */

// ====================================
// Inicialización
// ====================================

document.addEventListener('DOMContentLoaded', function() {
    initHamburgerMenu();
    initFormSubmitHandlers();
});

// ====================================
// Menú Hamburguesa
// ====================================

function initHamburgerMenu() {
    const hamburgerBtn = document.getElementById('hamburger-btn');
    const navMenu = document.getElementById('nav-menu');
    const navOverlay = document.getElementById('nav-overlay');
    const closeMenuBtn = document.getElementById('close-menu');

    if (!hamburgerBtn || !navMenu) return;

    // Abrir menú
    hamburgerBtn.addEventListener('click', function() {
        hamburgerBtn.classList.toggle('active');
        navMenu.classList.toggle('active');
        document.body.style.overflow = navMenu.classList.contains('active') ? 'hidden' : '';
    });

    // Cerrar menú - overlay
    if (navOverlay) {
        navOverlay.addEventListener('click', function() {
            closeMenu();
        });
    }

    // Cerrar menú - botón X
    if (closeMenuBtn) {
        closeMenuBtn.addEventListener('click', function() {
            closeMenu();
        });
    }

    // Cerrar menú - ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && navMenu.classList.contains('active')) {
            closeMenu();
        }
    });

    function closeMenu() {
        hamburgerBtn.classList.remove('active');
        navMenu.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// ====================================
// Manejo de Modales
// ====================================

function abrirModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function cerrarModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';

        // Limpiar contenido dinámico si existe
        const formContainer = modal.querySelector('#form-editar-container');
        if (formContainer) {
            formContainer.innerHTML = '';
        }
    }
}

// Cerrar modal al hacer clic en overlay
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal') && e.target.classList.contains('active')) {
        const modalId = e.target.id;
        cerrarModal(modalId);
    }
});

// Cerrar modal con ESC
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modalActivo = document.querySelector('.modal.active');
        if (modalActivo) {
            cerrarModal(modalActivo.id);
        }
    }
});

// ====================================
// Registro de Lecturas
// ====================================

/**
 * Abre el flujo de registro de lectura
 * Si cliente tiene 1 medidor -> formulario directo
 * Si cliente tiene múltiples medidores -> modal de selección
 */
function abrirRegistro(clienteId, numMedidores, clienteNombre) {
    if (numMedidores === 1) {
        // Obtener el medidor único y abrir formulario directo
        obtenerMedidoresCliente(clienteId).then(data => {
            if (data.medidores && data.medidores.length > 0) {
                const medidor = data.medidores[0];
                prepararFormularioRegistro(medidor.id, clienteNombre, medidor.numero_medidor);
            }
        });
    } else {
        // Mostrar modal de selección de medidores
        mostrarModalMedidores(clienteId, clienteNombre);
    }
}

/**
 * Obtiene medidores de un cliente vía API
 */
async function obtenerMedidoresCliente(clienteId) {
    try {
        const response = await fetch(`/mobile/api/medidores/${clienteId}`);
        if (!response.ok) throw new Error('Error al obtener medidores');
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        mostrarMensaje('Error al cargar medidores', 'error');
        return { medidores: [] };
    }
}

/**
 * Muestra modal con lista de medidores para seleccionar
 */
async function mostrarModalMedidores(clienteId, clienteNombre) {
    const data = await obtenerMedidoresCliente(clienteId);
    const medidoresContainer = document.getElementById('medidores-list');

    if (!medidoresContainer) return;

    medidoresContainer.innerHTML = '';

    if (data.medidores.length === 0) {
        medidoresContainer.innerHTML = '<p class="text-center text-muted">No hay medidores disponibles</p>';
        abrirModal('modal-medidores');
        return;
    }

    // Crear opciones de medidores
    data.medidores.forEach(medidor => {
        const option = document.createElement('div');
        option.className = 'medidor-option';
        option.innerHTML = `
            <strong>Medidor: ${medidor.numero_medidor || 'S/N'}</strong>
            <small>${medidor.direccion || 'Sin dirección'}</small>
        `;
        option.addEventListener('click', function() {
            cerrarModal('modal-medidores');
            prepararFormularioRegistro(medidor.id, clienteNombre, medidor.numero_medidor);
        });
        medidoresContainer.appendChild(option);
    });

    abrirModal('modal-medidores');
}

/**
 * Prepara y abre el formulario de registro
 */
function prepararFormularioRegistro(medidorId, clienteNombre, numeroMedidor) {
    const form = document.getElementById('form-registro-lectura');
    const titulo = document.getElementById('modal-registro-titulo');

    if (!form) return;

    // Actualizar título
    if (titulo) {
        titulo.textContent = `${clienteNombre} - Medidor: ${numeroMedidor || 'S/N'}`;
    }

    // Establecer medidor_id
    const medidorInput = document.getElementById('medidor-id');
    if (medidorInput) {
        medidorInput.value = medidorId;
    }

    // Limpiar formulario
    form.reset();
    document.getElementById('medidor-id').value = medidorId; // Mantener después del reset

    // Ocultar preview de foto
    const previewContainer = document.getElementById('foto-preview-container');
    if (previewContainer) {
        previewContainer.style.display = 'none';
    }

    // Ocultar mensaje
    const mensajeDiv = document.getElementById('form-mensaje');
    if (mensajeDiv) {
        mensajeDiv.style.display = 'none';
    }

    abrirModal('modal-registro');

    // Dar foco al campo de lectura
    setTimeout(() => {
        const lecturaInput = document.getElementById('lectura-m3');
        if (lecturaInput) lecturaInput.focus();
    }, 300);
}

/**
 * Maneja el envío del formulario de registro
 */
function initFormSubmitHandlers() {
    const formRegistro = document.getElementById('form-registro-lectura');

    if (formRegistro) {
        formRegistro.addEventListener('submit', async function(e) {
            e.preventDefault();

            const btnGuardar = document.getElementById('btn-guardar');
            const mensajeDiv = document.getElementById('form-mensaje');

            // Deshabilitar botón y mostrar loading
            const textoOriginal = btnGuardar.innerHTML;
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<span class="spinner"></span> Guardando...';

            // Ocultar mensajes previos
            if (mensajeDiv) {
                mensajeDiv.style.display = 'none';
            }

            try {
                const formData = new FormData(formRegistro);

                const response = await fetch('/mobile/lecturas/crear', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    // Éxito
                    btnGuardar.innerHTML = '<span>✓</span> Guardado';
                    btnGuardar.classList.remove('btn-primary');
                    btnGuardar.classList.add('btn-success');

                    if (mensajeDiv) {
                        mensajeDiv.textContent = result.message || 'Lectura registrada exitosamente';
                        mensajeDiv.className = 'form-mensaje success';
                        mensajeDiv.style.display = 'block';
                    }

                    // Recargar página después de 1 segundo
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    // Error
                    throw new Error(result.error || 'Error al guardar lectura');
                }

            } catch (error) {
                console.error('Error:', error);

                // Restaurar botón
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = textoOriginal;

                // Mostrar error
                if (mensajeDiv) {
                    mensajeDiv.textContent = error.message;
                    mensajeDiv.className = 'form-mensaje error';
                    mensajeDiv.style.display = 'block';
                }
            }
        });
    }
}

// ====================================
// Preview de Foto
// ====================================

function mostrarPreview(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();

        reader.onload = function(e) {
            const preview = document.getElementById('foto-preview');
            const previewContainer = document.getElementById('foto-preview-container');

            if (preview && previewContainer) {
                preview.src = e.target.result;
                previewContainer.style.display = 'block';
            }
        };

        reader.readAsDataURL(input.files[0]);
    }
}

function cambiarFoto() {
    const fotoInput = document.getElementById('foto');
    const previewContainer = document.getElementById('foto-preview-container');

    if (fotoInput) {
        fotoInput.value = '';
        fotoInput.click();
    }

    if (previewContainer) {
        previewContainer.style.display = 'none';
    }
}

// ====================================
// Edición de Lecturas
// ====================================

/**
 * Abre el formulario de edición de lectura
 * Primero valida que no tenga boleta asociada
 */
async function abrirEdicion(lecturaId) {
    try {
        // Validar si puede editar (no tiene boleta)
        const validacionResponse = await fetch(`/mobile/api/validar-edicion/${lecturaId}`);
        const validacion = await validacionResponse.json();

        if (!validacion.puede_editar) {
            alert(validacion.motivo || 'No se puede editar esta lectura');
            return;
        }

        // Obtener datos de la lectura
        const lecturaResponse = await fetch(`/mobile/api/lectura/${lecturaId}`);

        if (!lecturaResponse.ok) {
            throw new Error('Error al cargar lectura');
        }

        const lectura = await lecturaResponse.json();

        // Cargar formulario en el modal
        cargarFormularioEdicion(lectura);

    } catch (error) {
        console.error('Error:', error);
        alert('Error al abrir formulario de edición');
    }
}

/**
 * Carga el formulario de edición con los datos de la lectura
 */
function cargarFormularioEdicion(lectura) {
    const container = document.getElementById('form-editar-container');

    if (!container) return;

    container.innerHTML = `
        <form id="form-editar-lectura" class="form-mobile">
            <div class="form-group">
                <label for="editar-lectura-m3" class="form-label">Lectura (m³) *</label>
                <input type="number"
                       id="editar-lectura-m3"
                       name="lectura_m3"
                       class="input-mobile"
                       value="${lectura.lectura_m3}"
                       required
                       min="0"
                       inputmode="numeric"
                       pattern="[0-9]*"
                       autofocus>
            </div>

            <div class="form-group">
                <label for="editar-fecha" class="form-label">Fecha de Lectura</label>
                <input type="date"
                       id="editar-fecha"
                       name="fecha_lectura"
                       class="input-mobile"
                       value="${lectura.fecha_lectura}">
            </div>

            <div class="form-group">
                <p class="form-note">
                    <strong>Cliente:</strong> ${lectura.cliente_nombre}<br>
                    <strong>Medidor:</strong> ${lectura.numero_medidor || 'S/N'}<br>
                    <strong>Período:</strong> ${lectura.mes}/${lectura.anio}
                </p>
            </div>

            <div class="form-actions">
                <button type="button" class="btn-mobile btn-secondary" onclick="cerrarModal('modal-editar')">
                    Cancelar
                </button>
                <button type="submit" class="btn-mobile btn-primary" id="btn-actualizar">
                    Actualizar
                </button>
            </div>

            <div id="form-editar-mensaje" class="form-mensaje" style="display: none;"></div>
        </form>
    `;

    // Agregar event listener al formulario
    const form = document.getElementById('form-editar-lectura');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        handleSubmitEdicion(lectura.id);
    });

    abrirModal('modal-editar');

    // Dar foco al campo de lectura
    setTimeout(() => {
        const lecturaInput = document.getElementById('editar-lectura-m3');
        if (lecturaInput) lecturaInput.select();
    }, 300);
}

/**
 * Maneja el envío del formulario de edición
 */
async function handleSubmitEdicion(lecturaId) {
    const form = document.getElementById('form-editar-lectura');
    const btnActualizar = document.getElementById('btn-actualizar');
    const mensajeDiv = document.getElementById('form-editar-mensaje');

    // Deshabilitar botón y mostrar loading
    const textoOriginal = btnActualizar.innerHTML;
    btnActualizar.disabled = true;
    btnActualizar.innerHTML = '<span class="spinner"></span> Actualizando...';

    // Ocultar mensajes previos
    if (mensajeDiv) {
        mensajeDiv.style.display = 'none';
    }

    try {
        const formData = new FormData(form);

        const response = await fetch(`/mobile/lecturas/${lecturaId}/editar`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Éxito
            btnActualizar.innerHTML = '<span>✓</span> Actualizado';

            if (mensajeDiv) {
                mensajeDiv.textContent = result.message || 'Lectura actualizada exitosamente';
                mensajeDiv.className = 'form-mensaje success';
                mensajeDiv.style.display = 'block';
            }

            // Recargar página después de 1 segundo
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            // Error
            throw new Error(result.error || 'Error al actualizar lectura');
        }

    } catch (error) {
        console.error('Error:', error);

        // Restaurar botón
        btnActualizar.disabled = false;
        btnActualizar.innerHTML = textoOriginal;

        // Mostrar error
        if (mensajeDiv) {
            mensajeDiv.textContent = error.message;
            mensajeDiv.className = 'form-mensaje error';
            mensajeDiv.style.display = 'block';
        }
    }
}

// ====================================
// Utilidades
// ====================================

/**
 * Muestra mensaje de alerta temporal
 */
function mostrarMensaje(mensaje, tipo = 'error') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${tipo}`;
    alertDiv.textContent = mensaje;

    const container = document.querySelector('.mobile-container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);

        // Auto-ocultar después de 5 segundos
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}
