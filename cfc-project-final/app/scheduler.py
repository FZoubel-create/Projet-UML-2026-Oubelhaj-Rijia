from flask_apscheduler import APScheduler
from app import db
from app.models import Formation, EtatFormation, ActionLog
from datetime import datetime

scheduler = APScheduler()

def close_expired_inscriptions():
    """
    Tâche planifiée : Vérifie les formations dont la date de fermeture est passée
    et loggue l'événement de 'Fermeture Automatique'.
    
    Note: L'état 'Fermé' est implicite via les dates, mais nous voulons
    laisser une trace d'audit system (ActionLog) pour la conformité.
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        now = datetime.utcnow()
        # Trouver les formations publiées qui sont "expirées" mais qui n'ont pas encore de log de fermeture récent (optimisation)
        # Pour simplifier ici, on loggue juste le check global ou on itère.
        
        # On cherche les formations publiées dont la date_fermeture < now
        formations = Formation.query.filter(
            Formation.etat == EtatFormation.PUBLIEE,
            Formation.date_fermeture < now
        ).all()
        
        count = 0
        for f in formations:
            # Vérifier si on a déjà loggué la fermeture auto aujourd'hui pour éviter le spam de logs
            existing_log = ActionLog.query.filter_by(
                target_id=f.id, 
                target_type="Formation", 
                action="AUTO_CLOSURE_CHECK"
            ).order_by(ActionLog.timestamp.desc()).first()
            
            should_log = True
            if existing_log:
                # Si déjà checké aujourd'hui après la fermeture, on ignore
                if existing_log.timestamp > f.date_fermeture:
                    should_log = False
            
            if should_log:
                log = ActionLog(
                    user_id=None, # System
                    action="AUTO_CLOSURE_CHECK",
                    target_type="Formation", 
                    target_id=f.id,
                    details=f"Formation fermée aux inscriptions depuis {f.date_fermeture}"
                )
                db.session.add(log)
                count += 1
        
        if count > 0:
            db.session.commit()
            print(f"[Scheduler] {count} formations vérifiées et confirmées fermées.")
        else:
            # print("[Scheduler] Aucune nouvelle fermeture à signaler.")
            pass
