---
tipo: fornitore
nome: Esempio Fornitore SRL
piva: 00000000000
settore: metalli e leghe
referente_principale: Mario Esempio
ruolo_referente: commerciale
email_referente: mario@esempio-fornitore.it
telefono: +39 000 000000
relazione_dal: 2020-01
stato_relazione: attivo
ultimo_ordine: 2026-04-15
prodotti_forniti:
  - lamiere acciaio inox
  - profilati alluminio
condizioni_commerciali:
  sconto_listino: 5%
  termini_pagamento: 60gg DF
  trasporto: franco partenza
  resi: solo entro 15gg con DDT
affidabilita: alta
note_relazionali: |
  Template canonical per scheda fornitore. Campi obbligatori: tipo, nome.
  Tutti gli altri sono opzionali ma desiderabili. Il consulente compila in
  review le note_relazionali e i red_flag dopo l'estrazione LLM.
red_flag: []
---

# Esempio Fornitore SRL

Template di riferimento per la scheda fornitore. La struttura ricalca quella
della scheda cliente (vedi `clienti/rossetto-laminazioni.md`) ma con campi
ribilanciati sul punto di vista acquisto (prodotti_forniti, ultimo_ordine,
affidabilita).
