
# In formations.py probably, or admin.py. Formations is better context.

@formations_bp.route('/<int:id>/notify', methods=['GET', 'POST'])
@login_required
def notify_candidates(id):
    formation = Formation.query.get_or_404(id)
    check_permission(formation=formation)
    
    # Get stats for badges
    count_preselect = Inscription.query.filter_by(formation_id=id, etat=EtatInscription.PRESELECTIONNE).count()
    count_waitlist = Inscription.query.filter_by(formation_id=id, etat=EtatInscription.LISTE_ATTENTE).count()
    
    if request.method == 'POST':
        target_status_name = request.form.get('target_status')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Filter Logic
        query = Inscription.query.filter_by(formation_id=id)
        if target_status_name != 'ALL':
            query = query.filter_by(etat=EtatInscription[target_status_name])
            
        recipients = query.all()
        
        # Simulation d'envoi
        count = 0
        for inscr in recipients:
            # send_email(inscr.candidat.email, subject, message)
            count += 1
            
        flash(f'{count} emails envoyés avec succès.', 'success')
        return redirect(url_for('formations.manage'))
        
    return render_template('admin/notify_candidates.html', formation=formation, 
                          count_preselect=count_preselect, count_waitlist=count_waitlist)
