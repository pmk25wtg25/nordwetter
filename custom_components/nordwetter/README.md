# Nordwetter für Home Assistant

Diese native Home-Assistant-Integration stellt eine `weather`-Entität für einen konfigurierten Ort bereit. Die Daten stammen ohne API-Schlüssel vom öffentlichen JSON-Endpunkt von [wttr.in](https://wttr.in):

```text
https://wttr.in/<ORT>?format=j1
```

## Installation

### Manuell

1. Kopiere den Ordner `custom_components/nordwetter` in das Verzeichnis `config/custom_components/` deiner Home-Assistant-Installation.
2. Starte Home Assistant neu.
3. Öffne **Einstellungen > Geräte & Dienste > Integration hinzufügen** und suche nach **Nordwetter**.

### HACS

Das Verzeichnis enthält ein gültiges Home-Assistant-Manifest und ist für die Ablage als benutzerdefinierte HACS-Integration vorbereitet. Für HACS muss dieses Repository als benutzerdefiniertes Repository vom Typ **Integration** hinzugefügt und der Unterordner `custom_components/nordwetter` installiert werden. Die tatsächliche HACS-Verfügbarkeit hängt von der Repository-Konfiguration und HACS-Version ab.

## Konfiguration

Der Ort wird im Config Flow als Stadt- oder Ortsname eingegeben. Der Config Flow prüft den Namen, testet die Verbindung zu wttr.in und verhindert doppelte Einträge für denselben Ort. Es werden keine Zugangsdaten gespeichert.

Die Aktualisierung erfolgt standardmäßig höchstens einmal pro 60 Minuten über einen zentralen Datenkoordinator. Ein fehlgeschlagener späterer Abruf ersetzt die zuletzt erfolgreich geladenen Daten nicht; die Entität wird während des Fehlers als nicht verfügbar markiert.

## Unterstützte Daten

Die Entität stellt aktuelle Werte in den von wttr.in gelieferten Einheiten bereit:

- Wetterzustand, Temperatur und gefühlte Temperatur
- Luftfeuchtigkeit, Luftdruck und UV-Index
- Sichtweite
- Windgeschwindigkeit und Windrichtung
- Aktuelle Niederschlagsmenge als Zusatzattribut `current_precipitation` in `mm`
- Tagesvorhersagen mit Höchst-/Tiefsttemperatur
- Vorhersage-Niederschlagsmenge und maximale Niederschlagswahrscheinlichkeit aus Regen-, Schnee- und Gewitterwerten, sofern geliefert

Home Assistant übernimmt die Umrechnung in das konfigurierte Einheitensystem. Wetterbeschreibungen von wttr.in werden auf gültige Home-Assistant-Zustände wie `sunny`, `cloudy`, `rainy`, `snowy` und `fog` abgebildet.

Home Assistant definiert kein standardisiertes aktuelles Niederschlagsfeld für `WeatherEntity`. Deshalb wird die aktuelle Menge als `current_precipitation` mit `current_precipitation_unit: "mm"` bereitgestellt und nicht automatisch in die Benutzer-Einheit umgerechnet.

## Fehlerbehebung

- Bei einer Ersteinrichtung muss wttr.in erreichbar sein, da der Config Flow die Antwort testet.
- Prüfe bei `unavailable` zunächst die Netzwerkverbindung des Home-Assistant-Hosts und die Logs der Integration.
- Ein HTTP-Fehler, Timeout, ungültiges JSON oder eine unvollständige Antwort wird als Update-Fehler behandelt.
- Nach einem vorübergehenden Fehler wird beim nächsten erfolgreichen Intervall automatisch wieder aktualisiert.

## Einschränkungen

- Es gibt keine dokumentierte API-Authentifizierung und in diesem Projekt keine bestätigte Rate-Limit-Garantie von wttr.in.
- Der Dienst verwendet Ortsnamen; eine explizite Koordinatenauswahl oder Geolocation ist nicht implementiert.
- wttr.in liefert für Tagesvorhersagen datumsbasierte Werte ohne eine von dieser Integration ausgewertete Ortszeitzone. Die Forecast-Zeit wird deshalb als stabiler UTC-Mittagstimestamp dargestellt.
- Das feste Aktualisierungsintervall von 60 Minuten kann nicht über den Config Flow geändert werden.
- Verfügbarkeit und Datenumfang hängen vom öffentlichen wttr.in-Dienst und dessen Antwortformat ab.

## Lizenz und Herkunft

Die Integration ist Teil des Nordwetter-Repositories. Die Wetterdaten werden von wttr.in bereitgestellt; für dessen Nutzungsbedingungen und mögliche Dienstgrenzen ist der Betreiber von wttr.in maßgeblich.
