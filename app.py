import customtkinter as ctk
import pandas as pd

from scoring import get_top_1_recipe, get_alternatives
from ui_helpers import (
    display_label,
    extract_options,
    load_dataset,
    load_thumbnail_image,
    safe_text,
)


APP_BG_COLOR = "#efe9df"
PANEL_BG_COLOR = "#f7f1e7"
CARD_BG_COLOR = "#fffaf2"
SIDEBAR_BG_COLOR = "#26313d"
SIDEBAR_BUTTON_COLOR = "#334251"
SIDEBAR_BUTTON_HOVER_COLOR = "#415263"
ACCENT_COLOR = "#2f8f66"
TEXT_COLOR = "#1f2933"
MUTED_TEXT_COLOR = "#6b7280"
THUMBNAIL_SIZE = (96, 96)
ALT_THUMBNAIL_SIZE = (56, 56)
DATASET = load_dataset()
ALLERGY_OPTIONS = extract_options(DATASET, "allergens")
DIET_OPTIONS = extract_options(DATASET, "cultural_restriction")


class App(ctk.CTk):
    """
    Classe principale de l'application ThinkEat.
    Hérite de customtkinter.CTk pour créer une fenêtre principale.
    Gère l'architecture globale avec une barre latérale fixe et une zone principale.
    """


    def __init__(self):
        super().__init__()


        # Configuration de la fenêtre principale
        self.title("ThinkEat")
        self.geometry("1200x800")
        self.resizable(True, True)


        # Configuration du thème (optionnel, peut être ajusté)
        ctk.set_appearance_mode("System")  
        ctk.set_default_color_theme("blue")

        self.configure(fg_color=APP_BG_COLOR)

        # --- TRACKING GLOBAL POUR SWAP ---
        self.used_recipe_ids = set()  # Recettes utilisées dans la semaine
        self.current_menu = {}  # Structure: {jour: {repas: recipe_row}, ...}
        self.current_constraints = {}  # Stocke les contraintes pour le swap
        self.thumbnail_cache = {}
        
        # Création de la barre latérale (gauche)
        self.create_sidebar()


        # Création de la zone principale (droite)
        self.create_main_area()


        # Initialisation : afficher l'écran par défaut (Mes Contraintes)
        self.show_frame("contraintes")


    def create_sidebar(self):
        """
        Crée la barre latérale fixe à gauche.
        Contient le titre, les boutons de navigation et le bouton de génération.
        """
        # Frame de la barre latérale
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=SIDEBAR_BG_COLOR)
        self.sidebar_frame.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar_frame.pack_propagate(False)  # Empêche le redimensionnement automatique


        # Titre de l'application
        self.title_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="ThinkEat",
            text_color="white",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(20, 30))


        # Boutons de navigation
        self.nav_buttons = {}
        nav_items = [
            ("Mes Contraintes", "contraintes"),
            ("Mon Calendrier", "calendrier"),
            ("Mon Menu", "menu")
        ]


        for text, frame_name in nav_items:
            button = ctk.CTkButton(
                self.sidebar_frame,
                text=text,
                command=lambda fn=frame_name: self.show_frame(fn),
                height=40,
                font=ctk.CTkFont(size=14),
                fg_color=SIDEBAR_BUTTON_COLOR,
                hover_color=SIDEBAR_BUTTON_HOVER_COLOR,
                text_color="white",
            )
            button.pack(pady=5, padx=20, fill="x")
            self.nav_buttons[frame_name] = button


        # Bouton "Générer mon menu" en bas
        self.generate_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Générer mon menu",
            command=self.generate_menu,
            fg_color=ACCENT_COLOR,
            hover_color="#23906a",
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white",
        )
        self.generate_button.pack(side="bottom", pady=20, padx=20, fill="x")


    def create_main_area(self):
        """
        Crée la zone principale à droite.
        Contient les différents frames pour chaque écran.
        """
        # Frame conteneur pour la zone principale
        self.main_container = ctk.CTkFrame(self, fg_color=APP_BG_COLOR)
        self.main_container.pack(side="right", fill="both", expand=True, padx=10, pady=10)


        # Dictionnaire pour stocker les frames des écrans
        self.frames = {}


        # Création des 3 frames vides pour les écrans
        frame_names = ["contraintes", "calendrier", "menu"]
        for name in frame_names:
            frame = ctk.CTkFrame(self.main_container, fg_color=APP_BG_COLOR)
            self.frames[name] = frame


        # Construit les interfaces spécifiques aux écrans
        self.build_contraintes_ui()
        self.build_calendar_ui()
        self.build_menu_ui()


    def show_frame(self, frame_name):
        """
        Affiche le frame correspondant au nom passé en paramètre.
        Cache les autres frames.
        """
        # Cacher tous les frames
        for frame in self.frames.values():
            frame.pack_forget()


        # Afficher le frame demandé
        if frame_name in self.frames:
            self.frames[frame_name].pack(fill="both", expand=True)


    @staticmethod
    def parse_temps_max(value):
        """Convertit la valeur du combo temps en borne numerique exploitable par le scoring."""
        if value in ("120 ou +", "120+"):
            return float('inf')
        try:
            return int(value)
        except (ValueError, TypeError):
            return 30


    def build_contraintes_ui(self):
        """Construit les widgets pour l'écran "Mes Contraintes"."""
        frame = self.frames.get("contraintes")
        if frame is None:
            return


        # Titre global
        title = ctk.CTkLabel(
            frame,
            text="Quelles sont vos préférences ?",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_COLOR,
        )
        title.pack(pady=(20, 10))


        # --- Bloc 1 : Budget ---
        budget_label = ctk.CTkLabel(
            frame,
            text="Budget",
            font=ctk.CTkFont(size=16),
            text_color=TEXT_COLOR,
        )
        budget_label.pack(pady=(10, 0), anchor="w", padx=20)


        self.budget_var = ctk.StringVar(value="Standard")
        budget_options = ["Économique", "Standard", "Confort"]
        self.budget_seg = ctk.CTkSegmentedButton(
            frame,
            values=budget_options,
            variable=self.budget_var
        )
        self.budget_seg.pack(pady=(0, 10), padx=20, anchor="w")


        # --- Bloc 2 : Temps de préparation ---
        time_label = ctk.CTkLabel(
            frame,
            text="Temps maximum accordé",
            font=ctk.CTkFont(size=16),
            text_color=TEXT_COLOR,
        )
        time_label.pack(pady=(10, 0), anchor="w", padx=20)


        time_frame = ctk.CTkFrame(frame)
        time_frame.pack(pady=(0, 10), padx=20, fill="x")


        # Creer une liste de valeurs de temps (10, 20, 30... 110, puis 120 ou +)
        time_options = [str(x) for x in range(10, 120, 10)]
        time_options.append("120 ou +")
        
        self.time_var = ctk.StringVar(value="30")
        combobox = ctk.CTkComboBox(
            time_frame,
            values=time_options,
            variable=self.time_var,
        )
        combobox.pack(side="left", padx=(0, 10))


        # --- Bloc 3 : Allergies & Régimes séparés en deux colonnes ---
        preferences_label = ctk.CTkLabel(
            frame,
            text="Allergies & Régimes",
            font=ctk.CTkFont(size=16),
            text_color=TEXT_COLOR,
        )
        preferences_label.pack(pady=(10, 0), anchor="w", padx=20)


        preferences_frame = ctk.CTkFrame(frame, fg_color=PANEL_BG_COLOR)
        preferences_frame.pack(pady=(5, 10), padx=20, fill="both", expand=True)
        preferences_frame.grid_columnconfigure(0, weight=1)
        preferences_frame.grid_columnconfigure(1, weight=1)
        preferences_frame.grid_rowconfigure(0, weight=1)


        allergies_frame = ctk.CTkFrame(preferences_frame, fg_color=CARD_BG_COLOR)
        allergies_frame.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        allergies_title = ctk.CTkLabel(
            allergies_frame,
            text="Allergies",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_COLOR,
        )
        allergies_title.pack(pady=(10, 5), padx=10, anchor="w")

        allergies_scroll = ctk.CTkScrollableFrame(allergies_frame, height=240, fg_color=CARD_BG_COLOR)
        allergies_scroll.pack(padx=10, pady=(0, 10), fill="both", expand=True)

        self.allergy_vars = {}
        for item in ALLERGY_OPTIONS:
            var = ctk.BooleanVar()
            chk = ctk.CTkCheckBox(
                allergies_scroll,
                text=display_label(item),
                variable=var,
                text_color=TEXT_COLOR,
            )
            chk.pack(anchor="w", pady=2, padx=5)
            self.allergy_vars[item] = var


        diets_frame = ctk.CTkFrame(preferences_frame, fg_color=CARD_BG_COLOR)
        diets_frame.grid(row=0, column=1, padx=(10, 0), sticky="nsew")

        diets_title = ctk.CTkLabel(
            diets_frame,
            text="Régimes",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_COLOR,
        )
        diets_title.pack(pady=(10, 5), padx=10, anchor="w")

        diets_scroll = ctk.CTkScrollableFrame(diets_frame, height=240, fg_color=CARD_BG_COLOR)
        diets_scroll.pack(padx=10, pady=(0, 10), fill="both", expand=True)

        self.diet_vars = {}
        for item in DIET_OPTIONS:
            var = ctk.BooleanVar()
            chk = ctk.CTkCheckBox(
                diets_scroll,
                text=display_label(item),
                variable=var,
                text_color=TEXT_COLOR,
            )
            chk.pack(anchor="w", pady=2, padx=5)
            self.diet_vars[item] = var


    def generate_menu(self):
        """
        Méthode appelée par le bouton "Générer mon menu".
        Récupère les paramètres de l'utilisateur et affiche les recettes générées (1 par repas).
        """
        # 1. Récupérer le temps maximum et budget sélectionnés
        temps_max = self.parse_temps_max(self.time_var.get())
        budget = self.budget_var.get()

        # 1.b Récupérer allergies et régimes séparément
        allergies_user = [item for item, var in getattr(self, "allergy_vars", {}).items() if var.get()]
        diets_user = [item for item, var in getattr(self, "diet_vars", {}).items() if var.get()]
        
        # 2. Récupérer les jours et repas sélectionnés
        selected_meals = {}  # Structure: {jour: {repas: True/False, ...}, ...}
        
        for day, meal_vars in self.calendar_vars.items():
            selected_meals[day] = {}
            for meal, var in meal_vars.items():
                if var.get():  # Si coché
                    selected_meals[day][meal] = True
        
        # 3. Vérifier s'il y a au moins une sélection
        total_selected = sum(
            len([m for m, checked in meals.items() if checked])
            for meals in selected_meals.values()
        )
        
        if total_selected == 0:
            print(" Aucun repas sélectionné. Veuillez cocher au moins un repas.")
            return
        
        # 4. Réinitialiser le tracking
        self.used_recipe_ids = set()
        self.current_menu = {}
        self.current_constraints = {
            'temps_max_user': temps_max,
            'budget_user': budget,
            'allergies_user': allergies_user,
            'diets_user': diets_user,
        }
        
        # 5. Récupérer les recettes pour chaque jour/repas sélectionné (1 par repas)
        recipes_by_day_meal = {}  # Structure: {jour: {repas: recipe_row, ...}, ...}
        
        for day, meals in selected_meals.items():
            recipes_by_day_meal[day] = {}
            self.current_menu[day] = {}
            
            for meal, is_selected in meals.items():
                if is_selected:
                    # Appeler la fonction de scoring pour 1 recette (meilleure uniquement)
                    top_1 = get_top_1_recipe(
                        temps_max_user=temps_max,
                        budget_user=budget,
                        allergies_user=allergies_user,
                        diets_user=diets_user,
                        excluded_recipe_ids=list(self.used_recipe_ids),
                    )
                    
                    if top_1 is not None and not top_1.empty:
                        recipe = top_1.iloc[0]
                        recipe_id = recipe.get('recipeId', '')
                        
                        # Stocker la recette utilisée
                        self.used_recipe_ids.add(recipe_id)
                        recipes_by_day_meal[day][meal] = recipe
                        self.current_menu[day][meal] = recipe
                    else:
                        print(f" Erreur lors du chargement des recettes pour {day} {meal}")
        
        # 6. Afficher les résultats dans l'écran "Mon Menu"
        self.display_menu_results(recipes_by_day_meal)
        
        # 7. Naviguer vers l'écran "Mon Menu"
        self.show_frame("menu")
    
    
    def display_menu_results(self, recipes_by_day_meal):
        """
        Affiche les recettes générées dans l'écran "Mon Menu".
        recipes_by_day_meal : {jour: {repas: recipe_row, ...}, ...}
        Chaque repas a maintenant 1 recette (la meilleure), pas un DataFrame de 5.
        """
        # Effacer le contenu précédent du scroll
        for widget in self.menu_scroll.winfo_children():
            widget.destroy()
        
        # Ordre des jours pour l'affichage
        days_order = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        meals_order = ["Petit-déjeuner", "Déjeuner", "Dîner"]
        
        # Parcourir les jours et repas sélectionnés
        for day in days_order:
            if day not in recipes_by_day_meal or not recipes_by_day_meal[day]:
                continue
            
            # Afficher le titre du jour
            day_label = ctk.CTkLabel(
                self.menu_scroll,
                text=day,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=ACCENT_COLOR,
            )
            day_label.pack(pady=(15, 5), anchor="w", padx=10)
            
            # Parcourir les repas du jour
            for meal in meals_order:
                if meal not in recipes_by_day_meal[day]:
                    continue
                
                recipe = recipes_by_day_meal[day][meal]  # C'est maintenant une row, pas un DataFrame
                
                # Afficher le sous-titre du repas
                meal_label = ctk.CTkLabel(
                    self.menu_scroll,
                    text=f"  {meal}",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=TEXT_COLOR
                )
                meal_label.pack(pady=(5, 5), anchor="w", padx=30)
                
                # Afficher la recette pour ce repas
                self.create_recipe_card(self.menu_scroll, recipe, day, meal)
    
    
    # ----- Calendrier UI -----
    def select_all_meals(self):
        """Coche toutes les cases de repas du calendrier."""
        for day_vars in getattr(self, 'calendar_vars', {}).values():
            for var in day_vars.values():
                var.set(True)


    def deselect_all_meals(self):
        """Décoche toutes les cases de repas du calendrier."""
        for day_vars in getattr(self, 'calendar_vars', {}).values():
            for var in day_vars.values():
                var.set(False)


    def build_calendar_ui(self):
        """Construit les widgets pour l'écran "Mon Calendrier"."""
        frame = self.frames.get("calendrier")
        if frame is None:
            return


        # Titre global
        title = ctk.CTkLabel(
            frame,
            text="Planifiez vos repas de la semaine",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_COLOR,
        )
        title.pack(pady=(20, 10))


        # Boutons d'action rapide
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=(0, 10))


        all_btn = ctk.CTkButton(btn_frame, text="Tout cocher", command=self.select_all_meals)
        none_btn = ctk.CTkButton(btn_frame, text="Tout décocher", command=self.deselect_all_meals)
        all_btn.pack(side="left", padx=5)
        none_btn.pack(side="left", padx=5)


        # Conteneur pour les jours
        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)


        days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        self.calendar_vars = {}


        # Utiliser grid pour disposer 3+4 ou en colonne selon largeur
        for idx, day in enumerate(days):
            day_frame = ctk.CTkFrame(
                scroll,
                border_width=1,
                corner_radius=8,
                fg_color=SIDEBAR_BUTTON_COLOR,
                border_color=SIDEBAR_BUTTON_HOVER_COLOR,
            )
            row = idx // 3
            col = idx % 3
            day_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")


            label = ctk.CTkLabel(day_frame, text=day, font=ctk.CTkFont(size=14, weight="bold"), text_color="white")
            label.pack(pady=(5, 5))


            # Checkboxes pour les repas
            meals = ["Petit-déjeuner", "Déjeuner", "Dîner"]
            vars_for_day = {}
            for meal in meals:
                var = ctk.BooleanVar(value=True)
                chk = ctk.CTkCheckBox(day_frame, text=meal, variable=var, text_color="white")
                chk.pack(anchor="w", pady=2, padx=5)
                vars_for_day[meal] = var
            self.calendar_vars[day] = vars_for_day


        # Étendre colonnes pour une présentation uniforme
        for c in range(3):
            scroll.grid_columnconfigure(c, weight=1)


    # ----- Menu UI -----
    def build_menu_ui(self):
        """Construit les widgets pour l'écran "Mon Menu"."""
        frame = self.frames.get("menu")
        if frame is None:
            return

        # Zone centrale découpage 70/30
        content_frame = ctk.CTkFrame(frame, fg_color=APP_BG_COLOR)
        content_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))


        # Colonne repas (70%)
        meals_frame = ctk.CTkFrame(content_frame, fg_color=PANEL_BG_COLOR, corner_radius=16)
        meals_frame.pack(side="left", fill="both", expand=True)


        # Scroll pour les recettes - VIDE au démarrage, sera rempli par generate_menu()
        self.menu_scroll = ctk.CTkScrollableFrame(meals_frame, fg_color=PANEL_BG_COLOR)
        self.menu_scroll.pack(fill="both", expand=True)
        
        # Message initial
        empty_label = ctk.CTkLabel(
            self.menu_scroll,
            text="Générez vos menus pour voir les recettes",
            font=ctk.CTkFont(size=14),
            text_color=MUTED_TEXT_COLOR
        )
        empty_label.pack(pady=20)


        # Colonne swap (30%)
        self.swap_panel = ctk.CTkFrame(content_frame, width=200, fg_color=PANEL_BG_COLOR, corner_radius=16)
        self.swap_panel.pack(side="right", fill="y", padx=(10, 0))
        self.swap_panel.pack_propagate(False)

        swap_title = ctk.CTkLabel(
            self.swap_panel,
            text="Alternatives",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_COLOR,
        )
        swap_title.pack(pady=(10, 5))

        # Scroll pour les alternatives
        self.swap_scroll = ctk.CTkScrollableFrame(self.swap_panel, fg_color=PANEL_BG_COLOR)
        self.swap_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Message vide initial
        empty_swap = ctk.CTkLabel(
            self.swap_scroll,
            text="Cliquez sur 'Changer'\npour voir les alternatives",
            font=ctk.CTkFont(size=11),
            text_color=MUTED_TEXT_COLOR
        )
        empty_swap.pack(pady=20)

    
    def show_alternatives_for_meal(self, day, meal):
        """
        Affiche les 4 alternatives pour un repas sélectionné.
        day, meal : identifient le repas pour lequel on charge les alternatives.
        """
        # Vider le panneau swap
        for widget in self.swap_scroll.winfo_children():
            widget.destroy()
        
        # Afficher le titre du repas sélectionné
        meal_title = ctk.CTkLabel(
            self.swap_scroll,
            text=f"{day}\n{meal}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_COLOR
        )
        meal_title.pack(pady=(5, 10))
        
        # Divider
        divider = ctk.CTkFrame(self.swap_scroll, height=2, fg_color="#d7c9b4")
        divider.pack(fill="x", pady=5)
        
        # Charger les alternatives
        alternatives = get_alternatives(
            temps_max_user=self.current_constraints['temps_max_user'],
            budget_user=self.current_constraints['budget_user'],
            allergies_user=self.current_constraints['allergies_user'],
            diets_user=self.current_constraints['diets_user'],
            excluded_recipe_ids=list(self.used_recipe_ids),
            num_alternatives=4,
        )
        
        if alternatives is None or alternatives.empty:
            no_alt_label = ctk.CTkLabel(
                self.swap_scroll,
                text=" Aucune alternative\ndisponible",
                font=ctk.CTkFont(size=10),
                text_color="red"
            )
            no_alt_label.pack(pady=20)
            return
        
        # Afficher chaque alternative
        for idx, (_, alt_row) in enumerate(alternatives.iterrows(), start=1):
            self.create_alternative_button(day, meal, alt_row, idx)
    
    
    def create_alternative_button(self, day, meal, recipe_row, index):
        """
        Crée un bouton alternative avec nom, temps et score.
        """
        name = recipe_row.get('name', 'Recette inconnue')
        prep_time = recipe_row.get('prep_time', 'N/A')
        score = round(recipe_row.get('score_global', 0), 1)
        
        # Frame pour l'alternative
        alt_frame = ctk.CTkFrame(
            self.swap_scroll,
            fg_color=CARD_BG_COLOR,
            corner_radius=12,
            border_width=1,
            border_color="#e8dccb",
        )
        alt_frame.pack(fill="x", pady=5, padx=5)

        alt_image = self.get_recipe_thumbnail(recipe_row, ALT_THUMBNAIL_SIZE)
        alt_thumb = ctk.CTkLabel(
            alt_frame,
            text="",
            image=alt_image,
            width=ALT_THUMBNAIL_SIZE[0],
            height=ALT_THUMBNAIL_SIZE[1],
            fg_color=CARD_BG_COLOR,
        )
        alt_thumb.pack(side="left", padx=(8, 4), pady=8)
        alt_frame.thumbnail_image = alt_image
        
        # Contenu texte
        text_frame = ctk.CTkFrame(alt_frame, fg_color=CARD_BG_COLOR)
        text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        name_label = ctk.CTkLabel(
            text_frame,
            text=f"#{index} {name[:30]}",
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
            text_color=TEXT_COLOR,
        )
        name_label.pack(anchor="w", fill="x")
        
        time_label = ctk.CTkLabel(
            text_frame,
            text=f" {prep_time} min",
            font=ctk.CTkFont(size=9),
            anchor="w",
            text_color=MUTED_TEXT_COLOR
        )
        time_label.pack(anchor="w")
        
        score_label = ctk.CTkLabel(
            text_frame,
            text=f" {score}/100",
            font=ctk.CTkFont(size=9, weight="bold"),
            anchor="w",
            text_color=TEXT_COLOR,
        )
        score_label.pack(anchor="w")
        
        # Bouton de sélection
        select_btn = ctk.CTkButton(
            alt_frame,
            text="✓",
            command=lambda: self.apply_swap(day, meal, recipe_row),
            width=40,
            height=80,
            font=ctk.CTkFont(size=16),
            fg_color=ACCENT_COLOR,
            hover_color="#23906a",
        )
        select_btn.pack(side="right", padx=5, pady=5)
    
    
    def apply_swap(self, day, meal, new_recipe):
        """
        Applique le swap : remplace la recette du repas sélectionné.
        Met à jour le menu et réaffiche tout.
        """
        old_recipe = self.current_menu[day][meal]
        old_recipe_id = old_recipe.get('recipeId', '')
        new_recipe_id = new_recipe.get('recipeId', '')
        
        # Mettre à jour le tracking
        if old_recipe_id in self.used_recipe_ids:
            self.used_recipe_ids.remove(old_recipe_id)
        self.used_recipe_ids.add(new_recipe_id)
        
        # Mettre à jour le menu courant
        self.current_menu[day][meal] = new_recipe
        
        # Réafficher le menu
        self.display_menu_results(self.current_menu)
        
        # Vider le panneau d'alternatives
        for widget in self.swap_scroll.winfo_children():
            widget.destroy()
        
        empty_swap = ctk.CTkLabel(
            self.swap_scroll,
            text="Cliquez sur 'Changer'\npour voir les alternatives",
            font=ctk.CTkFont(size=11),
            text_color=MUTED_TEXT_COLOR
        )
        empty_swap.pack(pady=20)
        
        print(f"Swap effectué : {day} {meal} -> {new_recipe.get('name', 'Recette')}")


    def get_recipe_thumbnail(self, recipe_row, size=THUMBNAIL_SIZE):
        """Retourne une image CTkImage mise en cache pour une recette."""
        recipe_id = str(recipe_row.get("recipeId", "")).strip() or str(recipe_row.get("name", "")).strip()
        cache_key = f"{recipe_id}:{size[0]}x{size[1]}"

        if cache_key in self.thumbnail_cache:
            return self.thumbnail_cache[cache_key]

        url = recipe_row.get("thumbnail", "")
        pil_image = load_thumbnail_image(url, size)
        ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)
        self.thumbnail_cache[cache_key] = ctk_image
        return ctk_image


    def show_recipe_details(self, recipe_row):
        """Ouvre une fenêtre pop-up affichant les ingrédients et les instructions d'une recette."""
        recipe_name = safe_text(recipe_row.get("name"), "Recette")
        prep_time = safe_text(recipe_row.get("prep_time"), "N/A")
        score_global = recipe_row.get("score_global", None)
        score_text = f"{round(float(score_global), 1)}/100" if score_global not in (None, "", "N/A") and not pd.isna(score_global) else "N/A"

        ingredients_text = safe_text(recipe_row.get("ingredients_list"), "Aucun ingrédient disponible.")
        instructions_text = safe_text(recipe_row.get("instructions"), "Aucune instruction disponible.")

        popup = ctk.CTkToplevel(self)
        popup.title(recipe_name)
        popup.geometry("840x760")
        popup.configure(fg_color=APP_BG_COLOR)
        popup.transient(self)
        popup.grab_set()
        popup.lift()
        popup.focus_force()

        header = ctk.CTkFrame(popup, fg_color=PANEL_BG_COLOR, corner_radius=16)
        header.pack(fill="x", padx=20, pady=(20, 10))

        detail_image = self.get_recipe_thumbnail(recipe_row, size=(160, 160))
        image_label = ctk.CTkLabel(header, text="", image=detail_image)
        image_label.pack(side="left", padx=16, pady=16)
        header.detail_image = detail_image

        header_info = ctk.CTkFrame(header, fg_color=PANEL_BG_COLOR)
        header_info.pack(side="left", fill="both", expand=True, padx=(0, 16), pady=16)

        title_label = ctk.CTkLabel(
            header_info,
            text=recipe_name,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_COLOR,
            anchor="w",
        )
        title_label.pack(anchor="w", fill="x")

        meta_label = ctk.CTkLabel(
            header_info,
            text=f" {prep_time} min   •    {score_text}",
            font=ctk.CTkFont(size=12),
            text_color=MUTED_TEXT_COLOR,
            anchor="w",
        )
        meta_label.pack(anchor="w", pady=(4, 10))

        description_label = ctk.CTkLabel(
            header_info,
            text="Ingrédients et instructions de la recette sélectionnée.",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_COLOR,
            anchor="w",
            wraplength=560,
        )
        description_label.pack(anchor="w")

        content = ctk.CTkScrollableFrame(popup, fg_color=APP_BG_COLOR)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ingredients_title = ctk.CTkLabel(
            content,
            text="Ingrédients",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_COLOR,
        )
        ingredients_title.pack(anchor="w", pady=(10, 6))

        ingredients_box = ctk.CTkTextbox(
            content,
            height=200,
            fg_color=CARD_BG_COLOR,
            text_color=TEXT_COLOR,
            border_color="#e8dccb",
            wrap="word",
        )
        ingredients_box.pack(fill="x", pady=(0, 14))
        ingredients_box.insert("1.0", ingredients_text)
        ingredients_box.configure(state="disabled")

        instructions_title = ctk.CTkLabel(
            content,
            text="Instructions",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_COLOR,
        )
        instructions_title.pack(anchor="w", pady=(4, 6))

        instructions_box = ctk.CTkTextbox(
            content,
            height=300,
            fg_color=CARD_BG_COLOR,
            text_color=TEXT_COLOR,
            border_color="#e8dccb",
            wrap="word",
        )
        instructions_box.pack(fill="both", expand=True, pady=(0, 14))
        instructions_box.insert("1.0", instructions_text)
        instructions_box.configure(state="disabled")

        close_button = ctk.CTkButton(
            popup,
            text="Fermer",
            command=popup.destroy,
            fg_color=SIDEBAR_BUTTON_COLOR,
            hover_color=SIDEBAR_BUTTON_HOVER_COLOR,
            text_color="white",
        )
        close_button.pack(pady=(0, 20))


    def create_recipe_card(self, parent, recipe_row, day, meal):
        """
        Crée une carte de recette et l'ajoute au parent.
        recipe_row : row pandas contenant les infos de la recette.
        day, meal : jour et type de repas (pour tracker lors du swap)
        """
        # Récupérer les données de la recette
        name = recipe_row.get('name', 'Recette inconnue')
        prep_time = recipe_row.get('prep_time', 'N/A')
        score = round(recipe_row.get('score_global', 0), 1)

        # Créer la carte
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_BG_COLOR,
            corner_radius=14,
            border_width=1,
            border_color="#e8dccb",
        )
        card.pack(fill="x", pady=6, padx=20)

        # Thumbnail depuis le dataset
        thumbnail_image = self.get_recipe_thumbnail(recipe_row)
        thumb_label = ctk.CTkLabel(
            card,
            text="",
            image=thumbnail_image,
            width=THUMBNAIL_SIZE[0],
            height=THUMBNAIL_SIZE[1],
            fg_color=CARD_BG_COLOR,
        )
        thumb_label.pack(side="left", padx=(10, 8), pady=10)
        card.thumbnail_image = thumbnail_image

        # Info (nom, temps, score)
        info_frame = ctk.CTkFrame(card, fg_color=CARD_BG_COLOR)
        info_frame.pack(side="left", fill="both", expand=True, padx=5, pady=10)

        title = ctk.CTkLabel(
            info_frame,
            text=name[:45],
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            text_color=TEXT_COLOR,
        )
        title.pack(anchor="w", fill="x")

        time_lbl = ctk.CTkLabel(
            info_frame,
            text=f" {prep_time} min" if prep_time != 'N/A' else " N/A",
            font=ctk.CTkFont(size=10),
            anchor="w",
            text_color=MUTED_TEXT_COLOR,
        )
        time_lbl.pack(anchor="w")

        score_lbl = ctk.CTkLabel(
            info_frame,
            text=f" Score Global: {score}/100",
            font=ctk.CTkFont(size=10),
            anchor="w",
            text_color=TEXT_COLOR,
        )
        score_lbl.pack(anchor="w")

        # Actions
        action_frame = ctk.CTkFrame(card, fg_color=CARD_BG_COLOR)
        action_frame.pack(side="right", padx=10, pady=10)

        details_button = ctk.CTkButton(
            action_frame,
            text="Recette",
            command=lambda r=recipe_row: self.show_recipe_details(r),
            width=100,
            font=ctk.CTkFont(size=10),
            fg_color="#4a6fa5",
            hover_color="#3f5f90",
            text_color="white",
        )
        details_button.pack(fill="x")

        swap_button = ctk.CTkButton(
            action_frame,
            text=" Changer",
            command=lambda d=day, m=meal: self.show_alternatives_for_meal(d, m),
            width=100,
            font=ctk.CTkFont(size=10),
            fg_color=ACCENT_COLOR,
            hover_color="#23906a",
            text_color="white",
        )
        swap_button.pack(fill="x", pady=(8, 0))





