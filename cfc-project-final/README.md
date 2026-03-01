# Centre de Formation Continue (CFC) - University Management System

Une application web complète pour la gestion des formations continues universitaires, développée avec **Flask (Python)** et **Bootstrap 5**.

---

## 🚀 Installation & Lancement

### 1. Prérequis
*   Python 3.8+
*   pip (Gestionnaire de paquets Python)

### 2. Installation
Ouvrez un terminal dans le dossier du projet et exécutez :

```bash
# Installation des dépendances
pip install -r requirements.txt
```

### 3. Initialisation Base de Données
Le script de seeding crée la base de données et les utilisateurs de test :

```bash
# Initialise la BDD et ajoute les données de démo
python seed_data.py
```

### 4. Lancement
```bash
# Lancer le serveur de développement
python run.py
```
Accédez ensuite à l'application via : **http://127.0.0.1:5000**

---

## 🔑 Identifiants de Test (Demo)

Le système est pré-chargé avec 4 profils distincts pour tester le RBAC (Role-Based Access Control) :

| Rôle | Email | Mot de Passe | Description |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `super@cfc.ma` | `admin123` | Accès global (God Mode - Tour de Contrôle). |
| **Admin Etab.** | `admin.fst@usms.ma` | `fst123` | Gère les formations de la FST uniquement. |
| **Coordinateur** | `coord.info@fst.ma` | `coord123` | Gère l'ouverture des inscriptions "Big Data". |
| **Candidat** | `candidat@test.com` | `cand123` | Postule aux formations. |

---

## 🛠️ Stack Technique
*   **Backend** : Python, Flask, Flask-SQLAlchemy, Flask-Login, Flask-APScheduler.
*   **Frontend** : HTML5, CSS3, Bootstrap 5, Jinja2.
*   **Base de Données** : SQLite (Dev).
*   **Sécurité** : Hachage des mots de passe (Werkzeug), Protection CSRF, Session Secure.

---

**Auteurs** : Khadija RIJIA & Fatima Zahra Oubelhaj  
**Module** : UML & Génie Logiciel  
**Professeur** : Mr. Mohamed BINIZ
