from app import create_app, db
from app.models import Formation, EtatFormation
from datetime import datetime

app = create_app()

def close_expired_inscriptions():
    with app.app_context():
        now = datetime.utcnow()
        # Trouver les formations publiées dont la date de fermeture est passée
        # mais qui sont encore considérées comme "ouvertes" (si on avait un flag, ici on se base sur les dates)
        
        # Pour le log, on cherche celles dont date_fermeture < now
        formations = Formation.query.filter(
            Formation.etat == EtatFormation.PUBLIEE,
            Formation.date_fermeture < now
        ).all()
        
        count = 0
        for f in formations:
            # Ici, la logique "est_ouverte()" se base sur le temps réel.
            # Mais si on voulait changer un état explicite, on le ferait ici.
            # Pour l'instant, on va juste logger car notre modèle est dynamique (computed property)
            # Cependant, si on veut archiver les formations très anciennes :
            
            # Si fermée depuis plus de 90 jours -> Archivage
            delta = now - f.date_fermeture
            if delta.days > 90:
                f.etat = EtatFormation.ARCHIVEE
                count += 1
                print(f"Archivage auto de : {f.titre}")
        
        if count > 0:
            db.session.commit()
            print(f"Job terminé : {count} formations archivées.")
        else:
            print("Job terminé : Aucune formation à archiver.")

if __name__ == "__main__":
    print(">> Lancement du job nocturne de clôture...")
    close_expired_inscriptions()
