# Ollama Tray Controller

Prosta aplikacja zasobnika systemowego (system tray) dla KDE Plasma do zarządzania usługą Ollama.

![Screenshot aplikacji](screenshot.png)

## O projekcie

Ollama Tray Controller to lekka aplikacja napisana w Python z PyQt5, która umożliwia wygodne zarządzanie usługą Ollama z poziomu zasobnika systemowego. 

Główne funkcje:
- Widoczny wskaźnik statusu usługi Ollama (aktywna/nieaktywna)
- Prosta kontrola start/stop usługi Ollama
- Bezpieczne zapytanie o uprawnienia sudo
- Pełna integracja z KDE Plasma

## Wymagania

- Python 3.x
- PyQt5
- KDE Plasma (lub inne środowisko graficzne obsługujące QSystemTrayIcon)
- Zainstalowana usługa Ollama skonfigurowana do działania z systemd

## Instalacja

1. Zainstaluj wymagane zależności:

```bash
sudo pacman -S python-pyqt5
```

2. Sklonuj to repozytorium:

```bash
git clone https://github.com/zdziejowski/ollama-tray-controller.git
cd ollama-tray-controller
```

3. Ustaw uprawnienia do wykonywania:

```bash
chmod +x ollama_tray_kde.py
```

## Użycie

Uruchom aplikację z terminala:

```bash
./ollama_tray_kde.py
```

Lub dodaj ją do autostartu, aby uruchamiała się automatycznie po zalogowaniu.

## Dodawanie do autostartu

1. Utwórz plik .desktop w katalogu autostartu:

```bash
mkdir -p ~/.config/autostart
```

2. Utwórz plik `~/.config/autostart/ollama-tray-kde.desktop` o następującej zawartości:

```
[Desktop Entry]
Type=Application
Name=Ollama Tray
Comment=System tray app for Ollama control
Exec=/pełna/ścieżka/do/ollama_tray_kde.py
Icon=computer
Terminal=false
Categories=Utility;
StartupNotify=false
```

3. Zastąp `/pełna/ścieżka/do/` rzeczywistą ścieżką do skryptu.

## Jak to działa

Aplikacja regularnie sprawdza status usługi Ollama za pomocą `systemctl` i aktualizuje ikonę:
- Zielona ikona ✓: usługa uruchomiona
- Czerwona ikona ✗: usługa zatrzymana

Kliknięcie prawym przyciskiem myszy na ikonę pokazuje menu z opcjami:
- Status: informacja o aktualnym stanie
- Przełącz Ollama: zmienia stan usługi (wymaga hasła sudo)
- Zamknij: zamyka aplikację zasobnika

## Dostosowywanie

Możesz dostosować skrypt modyfikując:

- Interwał odświeżania statusu (domyślnie 5000ms):
  ```python
  self.timer.start(5000)  # Zmień na inną wartość w milisekundach
  ```

- Ikony statusu, zmieniając parametry `QIcon.fromTheme()`:
  ```python
  self.setIcon(QIcon.fromTheme("inna-ikona-systemowa"))
  ```

- Teksty w interfejsie, zmieniając odpowiednie ciągi znaków.

## Licencja

Ten projekt jest udostępniany na licencji MIT. Zobacz plik [LICENSE](LICENSE) dla szczegółów.

## Autor

Utworzone przez @zdziejowski

---

## Rozwiązywanie problemów

### Aplikacja nie pokazuje ikony w zasobniku

Upewnij się, że środowisko KDE ma włączoną obsługę zasobnika systemowego.

### Błędy uprawnień sudo

Upewnij się, że Twój użytkownik ma uprawnienia do wykonywania komend sudo dla systemctl.

### Niestandardowe ikony

Jeśli chcesz użyć niestandardowych ikon zamiast systemowych, zmień kod:

```python
# Z:
self.setIcon(QIcon.fromTheme("dialog-ok"))

# Na:
self.setIcon(QIcon("/ścieżka/do/ikony.png"))
```