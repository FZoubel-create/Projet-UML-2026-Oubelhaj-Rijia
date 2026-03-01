from app import create_app, db
from app.models import Etablissement, Formation, Utilisateur, RoleUtilisateur, EtatFormation
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def seed():
    app = create_app()
    with app.app_context():
        # Nettoyage (On vide les tables existantes pour éviter les doublons)
        db.drop_all()
        db.create_all()
        
        print(">> Base de données initialisée...")

        # 1. Création des Etablissements Réels (USMS)
        fst = Etablissement(
            nom="Faculté des Sciences et Techniques", 
            code="FST", 
            ville="Béni Mellal",
            image="gen_etab_fst_1769790986506.png"
        )
        encg = Etablissement(
            nom="École Nationale de Commerce et de Gestion", 
            code="ENCG", 
            ville="Béni Mellal",
            image="gen_etab_encg_1769791006560.png"
        )
        est = Etablissement(
            nom="École Supérieure de Technologie", 
            code="EST", 
            ville="Fkih Ben Salah",
            image="gen_etab_est_1769791027128.png"
        ) # Note: EST existe aussi à Beni Mellal, mais varié pour l'exemple

        db.session.add_all([fst, encg, est])
        db.session.commit()
        print(f">> 3 Etablissements créés (FST, ENCG, EST).")

        # 2. Création des Formations
        # --- Création des Formations ---
        # FST
        f_bigdata = Formation(
            titre="Master Ingénierie Big Data",
            description="Formation d'excellence en analyse de données massives...",
            etablissement_id=fst.id,
            etat=EtatFormation.PUBLIEE,
            categorie="Ingénierie",
            image="gen_fmt_bigdata_1769791046515.png",
            date_ouverture=datetime.utcnow(),
            date_fermeture=datetime.utcnow() + timedelta(days=30)
        )
        f_security = Formation(
            titre="Master Sécurité des Systèmes",
            description="Expertise en cybersécurité et audit...",
            etablissement_id=fst.id,
            etat=EtatFormation.PUBLIEE,
            categorie="Ingénierie",
            image="gen_fmt_security_1769791065998.png",
            date_ouverture=datetime.utcnow(),
            date_fermeture=datetime.utcnow() + timedelta(days=20)
        )
        f_biotech = Formation(
            titre="Ingénierie Biotechnologique",
            description="Application des biotechnologies à la santé...",
            etablissement_id=fst.id,
            etat=EtatFormation.PUBLIEE,
            categorie="Santé",
            image="gen_fmt_biotech_1769791140280.png",
            date_ouverture=datetime.utcnow(),
            date_fermeture=datetime.utcnow() + timedelta(days=15)
        )

        # ENCG
        f_audit = Formation(
            titre="Master Audit et Contrôle",
            description="Maîtrise des normes comptables et d'audit...",
            etablissement_id=encg.id,
            etat=EtatFormation.PUBLIEE,
            categorie="Management",
            image="gen_fmt_audit_1769791158863.png",
            date_ouverture=datetime.utcnow(),
            date_fermeture=datetime.utcnow() + timedelta(days=45)
        )
        f_marketing = Formation(
            titre="Master Marketing Digital",
            description="Stratégies digitales pour l'entreprise moderne...",
            etablissement_id=encg.id,
            etat=EtatFormation.PUBLIEE,
            categorie="Management",
            image="gen_fmt_marketing_1769791178293.png",
            date_ouverture=datetime.utcnow(),
            date_fermeture=datetime.utcnow() + timedelta(days=25)
        )

        # EST
        f_dev = Formation(
            titre="Licence Pro Développement Web",
            description="Développement full-stack moderne...",
            etablissement_id=est.id,
            etat=EtatFormation.PUBLIEE,
            categorie="Ingénierie",
            image="gen_fmt_dev_1769791198309.png",
            date_ouverture=datetime.utcnow(),
            date_fermeture=datetime.utcnow() + timedelta(days=10)
        )
        f_sport = Formation(
            titre="Management du Sport",
            description="Gestion des organizations sportives...",
            etablissement_id=est.id,
            etat=EtatFormation.PUBLIEE,
            categorie="Arts & Sport",
            image="gen_fmt_sport_1769791218625.png", # Using arts image for sport as grouping
            date_ouverture=datetime.utcnow(),
            date_fermeture=datetime.utcnow() + timedelta(days=30)
        )
        f_art = Formation(
            titre="Design et Arts Numériques",
            description="Création numérique et design d'interaction...",
            etablissement_id=est.id,
            etat=EtatFormation.PUBLIEE,
            categorie="Arts & Sport",
            image="gen_fmt_art_1769791395435.png",
            date_ouverture=datetime.utcnow(),
            date_fermeture=datetime.utcnow() + timedelta(days=40)
        )

        formations = [f_bigdata, f_security, f_biotech, f_audit, f_marketing, f_dev, f_sport, f_art]
        
        db.session.add_all(formations)
        db.session.commit()
        print(f">> {len(formations)} Formations créées et publiées.")

        # 3. Création des Utilisateurs (Super Admin)
        super_admin = Utilisateur(
            email="super@cfc.ma",
            password_hash=generate_password_hash("admin123"), 
            nom="Super",
            prenom="Admin",
            role=RoleUtilisateur.SUPER_ADMIN
        )
        
        # Admin Etab FST
        admin_fst = Utilisateur(
            email="admin.fst@usms.ma",
            password_hash=generate_password_hash("fst123"),
            nom="Admin",
            prenom="FST",
            role=RoleUtilisateur.ADMIN_ETABLISSEMENT,
            etablissement_id=fst.id
        )

        # Coordinateur (Big Data & Security) - FST
        coord_info = Utilisateur(
            email="coord.info@fst.ma",
            password_hash=generate_password_hash("coord123"),
            nom="Responsable",
            prenom="Info",
            role=RoleUtilisateur.COORDINATEUR
        )
        # Assignation des formations
        if f_bigdata: coord_info.formations_coordonnees.append(f_bigdata)
        if f_security: coord_info.formations_coordonnees.append(f_security)

        candidat = Utilisateur(
            email="candidat@test.com",
            password_hash=generate_password_hash("cand123"),
            nom="Etudiant",
            prenom="Test",
            role=RoleUtilisateur.CANDIDAT
        )

        db.session.add_all([super_admin, admin_fst, coord_info, candidat])
        db.session.commit()
        print(">> Utilisateurs Spéciaux créés :")
        print("   - Super Admin : super@cfc.ma")
        print("   - Admin FST   : admin.fst@usms.ma (Lié à FST)")
        print("   - Coord Info  : coord.info@fst.ma (Lié à BigData + Security)")
        print("   - Candidat    : candidat@test.com")
        print(">> SEEDING TERMINE AVEC SUCCES.")

if __name__ == "__main__":
    seed()
