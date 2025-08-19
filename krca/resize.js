// resize.js - Redimensionamiento desde cualquier fila
document.addEventListener('DOMContentLoaded', function() {
    const table = document.querySelector('table.resizable');
    if (!table) return;

    // Crear grips para headers
    const thElements = table.querySelectorAll('th');
    thElements.forEach(th => createGrip(th));

    // Crear grips para la primera fila de datos (opcional)
    const firstRowCells = table.querySelector('tbody tr:first-child td');
    if (firstRowCells) {
        firstRowCells.forEach(td => createGrip(td));
    }

    function createGrip(cell) {
        const grip = document.createElement('div');
        grip.className = 'grip';
        
        grip.addEventListener('mousedown', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const columnIndex = cell.cellIndex;
            const columnCells = Array.from(
                table.querySelectorAll(`tr > *:nth-child(${columnIndex + 1})`)
            );
            
            const startX = e.clientX;
            const startWidth = cell.offsetWidth;
            
            // Añadir clase de feedback visual a todas las celdas de la columna
            columnCells.forEach(c => c.classList.add('resizing'));
            grip.classList.add('active');
            
            document.body.style.userSelect = 'none';
            
            function doDrag(e) {
                const newWidth = startWidth + (e.clientX - startX);
                if (newWidth > 50 && newWidth < 500) {
                    columnCells.forEach(c => {
                        c.style.width = `${newWidth}px`;
                        c.style.minWidth = `${newWidth}px`;
                    });
                }
            }
            
            function stopDrag() {
                document.removeEventListener('mousemove', doDrag);
                document.removeEventListener('mouseup', stopDrag);
                columnCells.forEach(c => c.classList.remove('resizing'));
                grip.classList.remove('active');
                document.body.style.userSelect = '';
            }
            
            document.addEventListener('mousemove', doDrag);
            document.addEventListener('mouseup', stopDrag, { once: true });
        });
        
        cell.appendChild(grip);
    }
});
