# Homebrew

KRCA se distribuye a través de un **tap propio**:

```bash
brew install upszot/krca/krca
```

El tap es el repositorio `upszot/homebrew-krca`, que contiene
`Formula/krca.rb`.

## Por qué un tap y no `homebrew-core`

`homebrew-core` exige notabilidad (estrellas/forks/watchers). Mientras KRCA no
alcance esos umbrales, la vía correcta es un tap de terceros. Cuando el proyecto
crezca se puede proponer la fórmula a `homebrew-core`.

## Publicar una nueva versión

1. Publicar el `sdist` en PyPI (el workflow de release lo hace al crear un tag).
2. Obtener la URL y el `sha256` del `sdist`:

   ```bash
   curl -s https://pypi.org/pypi/krca/json \
     | jq -r '.urls[] | select(.packagetype=="sdist") | "\(.url)\n\(.digests.sha256)"'
   ```

3. Actualizar `url`, `sha256` y `version` implícita en la fórmula del tap:

   ```bash
   cd homebrew-krca
   brew bump-formula-pr --strict krca --url <url> --sha256 <sha256>
   # o editar Formula/krca.rb y luego:
   brew update-python-resources Formula/krca.rb
   ```

4. Validar:

   ```bash
   brew audit --strict --online krca
   brew style Formula/krca.rb
   brew install --build-from-source ./Formula/krca.rb
   brew test krca
   ```

5. Commit y push al repo del tap.

> **Nota sobre dependencias**: la fórmula fija `kubernetes` 36.x. A partir de
> `kubernetes` 37 se incorpora `pydantic`, cuyo `pydantic-core` requiere
> Rust/maturin y complica el build desde sdist en Homebrew. KRCA sólo requiere
> `kubernetes>=24.2.0`, así que 36.x es suficiente. Si se actualiza esa versión,
> verificá primero `brew install --build-from-source`.

## Crear el tap por primera vez

```bash
# En GitHub: crear el repo upszot/homebrew-krca (público, vacío)
git clone https://github.com/upszot/homebrew-krca.git
mkdir -p homebrew-krca/Formula
cp packaging/homebrew/Formula/krca.rb homebrew-krca/Formula/krca.rb
cd homebrew-krca
brew update-python-resources Formula/krca.rb
git add Formula/krca.rb
git commit -m "krca 6.0"
git push
```

Una vez publicado el tap:

```bash
brew tap upszot/krca
brew install krca
```
