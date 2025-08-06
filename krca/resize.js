// resize.js - Funcionalidad mejorada para redimensionamiento de columnas
document.addEventListener('DOMContentLoaded', function() {
    const thElements = document.querySelectorAll('th');
    
    thElements.forEach(th => {
        const grip = document.createElement('div');
        grip.className = 'grip';
        
        grip.addEventListener('mousedown', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const table = th.closest('table');
            const startX = e.clientX;
            const startWidth = th.offsetWidth;
            const nextTh = th.nextElementSibling;
            const startNextWidth = nextTh ? nextTh.offsetWidth : 0;
            
            // Añadir clase de retroalimentación visual
            th.classList.add('resizing');
            grip.classList.add('active');
            
            // Bloquear la selección de texto durante el arrastre
            document.body.style.userSelect = 'none';
            
            function doDrag(e) {
                const newWidth = startWidth + (e.clientX - startX);
                if (newWidth > 50 && newWidth < 500) {  // Límites de ancho
                    th.style.width = `${newWidth}px`;
                    
                    // Ajustar la columna siguiente si existe
                    if (nextTh) {
                        const newNextWidth = startNextWidth - (e.clientX - startX);
                        if (newNextWidth > 50) {
                            nextTh.style.width = `${newNextWidth}px`;
                        }
                    }
                }
            }
            
            function stopDrag() {
                document.removeEventListener('mousemove', doDrag);
                document.removeEventListener('mouseup', stopDrag);
                th.classList.remove('resizing');
                grip.classList.remove('active');
                document.body.style.userSelect = '';
            }
            
            document.addEventListener('mousemove', doDrag);
            document.addEventListener('mouseup', stopDrag, { once: true });
        });
        
        th.appendChild(grip);
    });
});
