from flask import Blueprint, render_template
from app.models import Formation, EtatFormation, Etablissement

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Afficher les 3 dernières formations publiées en vedette
    featured_formations = Formation.query.filter_by(etat=EtatFormation.PUBLIEE).order_by(Formation.id.desc()).limit(3).all()
    # Récupérer les établissements pour la section partenaires
    etablissements = Etablissement.query.all()
    return render_template('index.html', formations=featured_formations, etablissements=etablissements)

from flask import request

@main_bp.route('/catalogue')
def catalogue():
    search_query = request.args.get('q')
    category = request.args.get('category')
    etablissement_id = request.args.get('etablissement_id')
    page = request.args.get('page', 1, type=int)
    per_page = 9  # Grid 3x3
    
    query = Formation.query.filter_by(etat=EtatFormation.PUBLIEE)
    
    if search_query:
        query = query.filter(Formation.titre.ilike(f'%{search_query}%') | Formation.description.ilike(f'%{search_query}%'))
        
    if category:
        query = query.filter_by(categorie=category)
        
    if etablissement_id:
        query = query.filter_by(etablissement_id=etablissement_id)
        
    pagination = query.order_by(Formation.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    # Dynamic categories for filter
    # Note: In production, cache this or use a distinct query
    categories = ["Ingénierie", "Management", "Santé", "Arts & Sport", "Informatique"]
    
    return render_template('catalogue.html', 
                         pagination=pagination, 
                         active_category=category, 
                         active_etablissement=etablissement_id,
                         search_query=search_query,
                         categories=categories)

@main_bp.route('/formation/<int:id>')
def detail(id):
    formation = Formation.query.get_or_404(id)
    # Vérifier que la formation est publiée, sauf si admin
    # Pour l'instant simple: si pas publiée et pas admin -> 404 ou 403
    # On va assumer que tout le monde peut voir les pages, mais le bouton postuler sera désactivé si pas ouverte
    return render_template('formation_detail.html', formation=formation)

@main_bp.route('/etablissements')
def etablissements():
    etablissements = Etablissement.query.all()
    return render_template('etablissements.html', etablissements=etablissements)

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    # Simple GET pour l'instant (Formulaire visuel)
    return render_template('contact.html')

@main_bp.route('/apropos')
def apropos():
    return render_template('apropos.html')
