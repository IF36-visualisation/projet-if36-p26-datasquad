# =============================================================================
#  Application Shiny — Explorateur morphologique des athlètes olympiques
#  Projet IF36 - DataSquad
# =============================================================================


library(shiny)          
library(shinydashboard)  
library(tidyverse)

# --- Chargement des données ---
# L'application est dans /shiny/ ; les données sont dans /data/.
# On essaie d'abord le chemin relatif "../data/", sinon le dossier courant.
chemin_donnees <- if (file.exists("../data/olympics_athletes_dataset.csv")) {
  "../data/olympics_athletes_dataset.csv"
} else {
  "olympics_athletes_dataset.csv"  # cas écheant : copie dans /shiny/
}

# On lit le fichier et on calcule l'IMC une fois pour toutes.
donnees <- read_csv(chemin_donnees, show_col_types = FALSE) %>%
  mutate(imc = weight_kg / (height_cm / 100)^2)

# Liste triée des disciplines, pour alimenter les menus déroulants.
liste_sports <- sort(unique(donnees$sport))

# =============================================================================
#  INTERFACE UTILISATEUR (UI)
# =============================================================================
ui <- dashboardPage(

  # En-tête du tableau de bord.
  dashboardHeader(title = "Explorateur morphologique"),

  # Barre latérale : les deux onglets de l'application.
  dashboardSidebar(
    sidebarMenu(
      menuItem("Nuage taille / poids", tabName = "nuage", icon = icon("braille")),
      menuItem("Distribution de l'IMC", tabName = "imc",   icon = icon("chart-area"))
    )
  ),

  # Corps du tableau de bord.
  dashboardBody(
    tabItems(

      # ----- Onglet 1 : nuage de points taille x poids -----
      tabItem(
        tabName = "nuage",
        fluidRow(
          # Colonne de gauche : les contrôles interactifs.
          box(
            title = "Filtres", status = "primary", solidHeader = TRUE, width = 3,
            # Choix d'UNE discipline.
            selectInput("sport_choisi", "Discipline :",
                        choices = liste_sports, selected = "Basketball"),
            # Choix de la saison (les deux cochées par défaut).
            checkboxGroupInput("saison", "Saison :",
                               choices = c("Summer", "Winter"),
                               selected = c("Summer", "Winter")),
            # Choix du genre.
            radioButtons("genre", "Genre :",
                         choices = c("Tous", "Female", "Male"), selected = "Tous")
          ),
          # Colonne de droite : le graphique + un indicateur de comptage.
          box(
            title = "Nuage taille x poids (couleur = médaille)",
            status = "primary", solidHeader = TRUE, width = 9,
            plotOutput("graph_nuage", height = "480px"),
            valueBoxOutput("nb_athletes", width = 12)
          )
        )
      ),

      # ----- Onglet 2 : distribution de l'IMC -----
      tabItem(
        tabName = "imc",
        fluidRow(
          box(
            title = "Filtres", status = "warning", solidHeader = TRUE, width = 3,
            # Choix de PLUSIEURS disciplines à comparer.
            selectInput("sports_imc", "Disciplines à comparer :",
                        choices = liste_sports,
                        selected = c("Weightlifting", "Swimming", "Gymnastics (Artistic)"),
                        multiple = TRUE)
          ),
          box(
            title = "Distribution de l'IMC par discipline",
            status = "warning", solidHeader = TRUE, width = 9,
            plotOutput("graph_imc", height = "480px")
          )
        )
      )
    )
  )
)

# =============================================================================
#  LOGIQUE SERVEUR (SERVER)
# =============================================================================
server <- function(input, output) {

  # --- Données filtrées de façon réactive pour l'onglet 1 ---
  donnees_filtrees <- reactive({
    d <- donnees %>%
      filter(sport == input$sport_choisi,         # discipline choisie
             games_type %in% input$saison)         # saison(s) cochée(s)
    # Filtre optionnel sur le genre.
    if (input$genre != "Tous") {
      d <- d %>% filter(gender == input$genre)
    }
    d
  })

  # --- Graphique de l'onglet 1 : nuage taille x poids ---
  output$graph_nuage <- renderPlot({
    ggplot(donnees_filtrees(), aes(x = height_cm, y = weight_kg, colour = medal)) +
      geom_point(size = 2, alpha = 0.7) +
      labs(x = "Taille (cm)", y = "Poids (kg)", colour = "Médaille",
           title = paste("Discipline :", input$sport_choisi)) +
      theme_minimal(base_size = 14)
  })

  # --- Indicateur du nombre d'athlètes correspondant aux filtres ---
  output$nb_athletes <- renderValueBox({
    valueBox(
      value = nrow(donnees_filtrees()),
      subtitle = "athlètes correspondant aux filtres",
      icon = icon("users"), color = "blue"
    )
  })

  # --- Graphique de l'onglet 2 : violons d'IMC pour les disciplines choisies ---
  output$graph_imc <- renderPlot({
    # Sécurité : si l'utilisateur n'a sélectionné aucun sport, on ne trace rien.
    req(input$sports_imc)
    donnees %>%
      filter(sport %in% input$sports_imc) %>%
      ggplot(aes(x = sport, y = imc, fill = sport)) +
      geom_violin(scale = "width", colour = "grey40") +
      geom_boxplot(width = 0.1, fill = "white", alpha = 0.6, outlier.shape = NA) +
      labs(x = "Discipline", y = "IMC", title = "Comparaison de l'IMC") +
      theme_minimal(base_size = 14) +
      theme(legend.position = "none")
  })
}

# =============================================================================
#  LANCEMENT DE L'APPLICATION
# =============================================================================
shinyApp(ui = ui, server = server)