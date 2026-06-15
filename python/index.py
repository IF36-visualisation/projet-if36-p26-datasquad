import os
import csv
import sys
import subprocess

# Fonction pour installer et importer matplotlib automatiquement
def import_or_install_matplotlib():
    try:
        import matplotlib
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        return plt, patches
    except ImportError:
        print("matplotlib n'est pas détecté. Tentative d'installation automatique via pip...")
        try:
            # Utilisation de sys.executable pour exécuter le pip de l'installation Python courante
            subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib"])
            import matplotlib
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches
            print("matplotlib installé avec succès !")
            return plt, patches
        except Exception as e:
            print(f"Impossible d'installer automatiquement matplotlib : {e}")
            print("Veuillez installer matplotlib manuellement avec la commande : python -m pip install matplotlib")
            return None, None

def pearson_correlation(x, y):
    # Pairwise complete observations
    clean_x, clean_y = [], []
    for xi, yi in zip(x, y):
        if xi is not None and yi is not None:
            clean_x.append(xi)
            clean_y.append(yi)
            
    n = len(clean_x)
    if n < 2:
        return None
    mean_x = sum(clean_x) / n
    mean_y = sum(clean_y) / n
    
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(clean_x, clean_y))
    den_x = sum((xi - mean_x) ** 2 for xi in clean_x)
    den_y = sum((yi - mean_y) ** 2 for yi in clean_y)
    
    if den_x == 0 or den_y == 0:
        return None
    return num / ((den_x * den_y) ** 0.5)

def main():
    # Détermination du chemin du fichier CSV de manière robuste
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, '..', 'data', 'olympics_athletes_dataset.csv')
    
    if not os.path.exists(csv_path):
        print(f"Erreur : Le fichier dataset est introuvable au chemin : {csv_path}")
        return

    print("Chargement et traitement des données (via la bibliothèque standard)...")
    
    # Exclusion des identifiants et textes libres à forte cardinalité
    exclude_cols = {"athlete_id", "athlete_name", "date_of_birth", "coach_name", "notes"}
    
    # Lecture des données
    raw_data = []
    headers = []
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            for row in reader:
                raw_data.append(row)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier CSV : {e}")
        return

    # Identification des colonnes à conserver
    keep_indices = [i for i, h in enumerate(headers) if h not in exclude_cols]
    keep_headers = [headers[i] for i in keep_indices]
    
    # Encodage de medal
    medal_mapping = {"None": 1, "No Medal": 1, "Bronze": 2, "Silver": 3, "Gold": 4}
    
    # Analyse des valeurs uniques pour les variables catégorielles afin de les encoder
    categories = {h: set() for h in keep_headers}
    for row in raw_data:
        for idx, h in zip(keep_indices, keep_headers):
            val = row[idx].strip()
            if val != "" and val != "-":
                categories[h].add(val)
                
    # Création des dictionnaires d'encodage (triés par ordre alphabétique comme les facteurs R)
    label_encoders = {}
    for h, vals in categories.items():
        if h == "medal":
            continue
        # Si la colonne contient des lettres, on l'encode
        is_numeric = True
        for v in vals:
            try:
                float(v)
            except ValueError:
                is_numeric = False
                break
        if not is_numeric:
            sorted_vals = sorted(list(vals))
            label_encoders[h] = {v: i + 1 for i, v in enumerate(sorted_vals)}

    # Conversion des données en vecteurs numériques
    processed_cols = {h: [] for h in keep_headers}
    for row in raw_data:
        for idx, h in zip(keep_indices, keep_headers):
            val = row[idx].strip()
            if val == "" or val == "-":
                processed_cols[h].append(None)
                continue
            
            if h == "medal":
                processed_cols[h].append(medal_mapping.get(val, 1))
            elif h in label_encoders:
                processed_cols[h].append(label_encoders[h].get(val, None))
            else:
                try:
                    processed_cols[h].append(float(val))
                except ValueError:
                    processed_cols[h].append(None)

    # Filtrer les colonnes qui n'ont pas assez de valeurs ou qui n'ont aucune variation
    final_headers = []
    final_data = {}
    for h in keep_headers:
        valid_vals = [v for v in processed_cols[h] if v is not None]
        if len(valid_vals) > 1 and len(set(valid_vals)) > 1:
            final_headers.append(h)
            final_data[h] = processed_cols[h]

    n_vars = len(final_headers)
    print(f"Calcul de la matrice de corrélation pour {n_vars} variables...")
    
    # Calcul de la matrice de corrélation (triangle inférieur uniquement, diagonale exclue)
    correlations = {}
    for i in range(n_vars):
        for j in range(i):
            h1 = final_headers[i]
            h2 = final_headers[j]
            r = pearson_correlation(final_data[h1], final_data[h2])
            correlations[(h1, h2)] = r

    # 1. Génération de l'HTML/CSS Premium interactif
    html_path = os.path.join(script_dir, "correlation_heatmap.html")
    print(f"Génération de la heatmap HTML sous : {html_path} ...")
    
    def get_color(r):
        if r is None:
            return "rgba(240, 240, 240, 0.5)"
        if r >= 0:
            return f"rgba(231, 76, 60, {r:.2f})"
        else:
            return f"rgba(59, 89, 152, {abs(r):.2f})"

    def get_text_color(r):
        if r is None:
            return "#aaa"
        if abs(r) > 0.5:
            return "#fff"
        return "#2c3e50"

    table_rows = []
    x_headers = final_headers[:-1]
    y_headers = list(reversed(final_headers[1:]))
    
    for row_h in y_headers:
        row_cells = [f'<td class="row-label">{row_h}</td>']
        for col_h in x_headers:
            r = None
            idx_row = final_headers.index(row_h)
            idx_col = final_headers.index(col_h)
            if idx_row > idx_col:
                r = correlations.get((row_h, col_h))
                
            if r is not None:
                color = get_color(r)
                text_color = get_text_color(r)
                cell_html = f'<td style="background-color: {color}; color: {text_color};" title="{col_h} &times; {row_h} : {r:.4f}">{r:.2f}</td>'
            else:
                cell_html = '<td class="empty-cell"></td>'
            row_cells.append(cell_html)
        table_rows.append(f"<tr>{''.join(row_cells)}</tr>")
        
    x_headers_html = "".join(f'<th class="col-label"><div><span>{h}</span></div></th>' for h in x_headers)

    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Heatmap des Corrélations</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            margin: 0;
            padding: 40px;
            color: #2c3e50;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            max-width: 95%;
            overflow-x: auto;
            border: 1px solid rgba(255, 255, 255, 0.5);
        }}
        h1 {{
            font-weight: 600;
            margin-top: 0;
            text-align: center;
            font-size: 28px;
            background: linear-gradient(45deg, #3b5998, #e74c3c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 30px;
        }}
        table {{
            border-collapse: collapse;
            margin: 0 auto;
        }}
        th, td {{
            width: 45px;
            height: 45px;
            text-align: center;
            font-size: 11px;
            font-weight: 600;
            border: 1px solid #ffffff;
            transition: all 0.2s ease;
        }}
        td:not(.empty-cell):not(.row-label):hover {{
            transform: scale(1.15);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            z-index: 10;
            position: relative;
            cursor: pointer;
            border-radius: 4px;
        }}
        .row-label {{
            width: auto;
            text-align: right;
            padding-right: 15px;
            font-size: 12px;
            font-weight: 400;
            color: #555;
            background: none;
            border: none;
            white-space: nowrap;
        }}
        .col-label {{
            height: 120px;
            vertical-align: bottom;
            border: none;
            background: none;
        }}
        .col-label div {{
            transform: rotate(-45deg) translate(5px, 0px);
            width: 45px;
            white-space: nowrap;
        }}
        .col-label span {{
            font-size: 12px;
            font-weight: 400;
            color: #555;
            display: inline-block;
            text-align: left;
            width: 120px;
        }}
        .empty-cell {{
            background: transparent;
            border: none;
        }}
        .legend {{
            display: flex;
            justify-content: center;
            margin-top: 35px;
            gap: 20px;
            font-size: 13px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .color-box {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Matrice de Corrélation des Variables (Triangle Inférieur)</h1>
        <table>
            <thead>
                <tr>
                    <th></th>
                    {x_headers_html}
                </tr>
            </thead>
            <tbody>
                {"".join(table_rows)}
            </tbody>
        </table>
        
        <div class="legend">
            <div class="legend-item">
                <div class="color-box" style="background-color: #3b5998;"></div>
                <span>Corrélation Négative (max -1.00)</span>
            </div>
            <div class="legend-item">
                <div class="color-box" style="background-color: #f7f7f7; border: 1px solid #ccc;"></div>
                <span>Neutre (0.00)</span>
            </div>
            <div class="legend-item">
                <div class="color-box" style="background-color: #e74c3c;"></div>
                <span>Corrélation Positive (max +1.00)</span>
            </div>
        </div>
    </div>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 2. Génération de la heatmap graphique via matplotlib (si disponible ou installé)
    plt, patches = import_or_install_matplotlib()
    if plt is not None and patches is not None:
        png_path = os.path.join(script_dir, "correlation_heatmap.png")
        print(f"Génération de l'image graphique de la heatmap sous : {png_path} ...")
        
        fig, ax = plt.subplots(figsize=(14, 12))
        
        # Inversion de y pour avoir la première en haut (comme le HTML)
        y_vars = list(reversed(final_headers[1:]))
        x_vars = final_headers[:-1]
        
        # Tracé des carrés
        for i, y_var in enumerate(y_vars):
            for j, x_var in enumerate(x_vars):
                idx_row = final_headers.index(y_var)
                idx_col = final_headers.index(x_var)
                
                # Seulement sous la diagonale
                if idx_row > idx_col:
                    r = correlations.get((y_var, x_var))
                    if r is not None:
                        # Définition de la couleur (de bleu à rouge)
                        if r >= 0:
                            # Rouge
                            color = (1.0, 1 - r, 1 - r)  # Rouge vif pour r=1, blanc pour r=0
                        else:
                            # Bleu
                            color = (1 - abs(r), 1 - abs(r), 1.0)  # Bleu vif pour r=-1, blanc pour r=0
                            
                        # Dessin du rectangle
                        rect = patches.Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor=color, edgecolor='white', linewidth=1)
                        ax.add_patch(rect)
                        
                        # Ajout du texte
                        text_color = 'white' if abs(r) > 0.5 else 'black'
                        ax.text(j, i, f"{r:.2f}", ha="center", va="center", color=text_color, fontsize=9, fontweight='bold')
        
        # Configuration des axes
        ax.set_xticks(range(len(x_vars)))
        ax.set_xticklabels(x_vars, rotation=45, ha="right", rotation_mode="anchor")
        ax.set_yticks(range(len(y_vars)))
        ax.set_yticklabels(y_vars)
        
        ax.set_xlim(-0.5, len(x_vars) - 0.5)
        ax.set_ylim(-0.5, len(y_vars) - 0.5)
        ax.set_aspect('equal')
        
        # Suppression des lignes de bordure
        for spine in ax.spines.values():
            spine.set_visible(False)
            
        plt.title("Matrice de Corrélation des Variables du Dataset (Triangle Inférieur)", fontsize=16, fontweight='bold', pad=20)
        plt.tight_layout()
        
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        plt.close()
        print("Succès ! L'image correlation_heatmap.png a été générée.")
    else:
        print("\nNote : matplotlib n'a pas pu être importé ou installé.")
        print("Seul le fichier HTML a été mis à jour.")

if __name__ == '__main__':
    main()
