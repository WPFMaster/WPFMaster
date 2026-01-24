\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{MO}[2025/11/15 Document class for Mathematic Olympiad documents]

\LoadClass[12pt, a4paper]{article}

\RequirePackage[utf8]{inputenc}
\RequirePackage[czech]{babel}
\RequirePackage{csquotes}
\RequirePackage{geometry}
\RequirePackage{tikz}
\usetikzlibrary{shapes.geometric, calc}
\RequirePackage{tkz-euclide}
\RequirePackage{amsmath, yhmath, amssymb, physics}
\RequirePackage{enumitem}
\RequirePackage{fancyhdr} % Required for headers

%%%%%% Rozměry
\geometry{
    a4paper,
    total={150mm,237mm},
    left=20mm,
    top=30mm,
    headheight=60pt, % Increased to accommodate 3 lines of text
    headsep=15pt
}

%%%%%% Custom math commands
\newcommand{\ddx}[1]{\dv{#1}{x}}
\newcommand{\dydx}[0]{\dv{y}{x}}
% Usage: \ddx{y} -> dy/dx

%%%%%% Commands for metadata
\newcommand{\studentclass}[1]{\def\@studentclass{#1}}
\newcommand{\school}[1]{\def\@school{#1}}
\newcommand{\problemcategory}[4]{\def\@probcat{#1.~#2-#3-#4}}

%%%%%% PŘÍKAZY
\newcommand{\B}{\textbf} % tučné písmo
\newcommand{\It}{\textit} % kurzíva

%%%%%% Header Setup
\pagestyle{fancy}
\fancyhf{} % Clear defaults
\renewcommand{\headrulewidth}{1pt} % The horizontal line

% Standard header for pages 2 and onwards
\fancyhead[L]{\@author \\ \@probcat}
\fancyhead[R]{\thepage.}

% Special header for the first page
\fancypagestyle{firstpage}{
    \fancyhf{}
    \fancyhead[L]{\@author \\ \@studentclass \\ \@school \\ \@probcat}
    \fancyhead[R]{\thepage.}
    \renewcommand{\headrulewidth}{1pt}
}

%%%%%% Category Printing logic
\newcommand{\makeMOheader}{
    \thispagestyle{firstpage}
    %\vspace*{1em}
    \par
}