;
; Emacs major mode for editing Evennia batch-command files (*.ev files). 
; Griatch 2011-09. Tested with GNU Emacs 23. Released under same license as Evennia.
;
; For batch-code files it's better to simply use the normal Python mode. 
;
; Features: 
;  Syntax hilighting
;  Auto-indenting properly when pressing <tab>. 
; 
; Installation: 
;   - Copy this file, evennia-mode.el, to a location where emacs looks for plugins
;     (usually .emacs.d/ at least under Linux)
;   - If you don't have that directory, either look on the web for how to find it 
;     or create it yourself - create a new directory .emacs.d/ some place and add 
;     the following to emacs' configuration file (.emacs):
;        (add-to-list 'load-path "<PATH>/.emacs.d/")
;     where PATH is the place you created the directory. Now Emacs will know to
;     look here for plugins. Copy this file there.
;   - In emacs config file (.emacs), next add the following line:
;        (require 'evennia-mode)    
;   - (re)start emacs 
;   - Open a batch file with the ending *.ev. The mode will start automatically
;     (otherwise you can manually start it with M-x evennia-mode).     
;
;   Report bugs to evennia's issue tracker.
;

(defvar evennia-mode-hook nil)

; Add keyboard shortcuts (not used)
(defvar evennia-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map "\C-j" 'newline-and-indent)
    map)
  "Keymap for evennia major mode")

; Autoload this when .ev file opens.
(add-to-list 'auto-mode-alist '("\\.ev\\'" . evennia-mode))

; Syntax hilighting
(defconst evennia-font-lock-keywords
  (list
   '("^ *#.*" . font-lock-comment-face)
   '("^[^ |^#]*" . font-lock-variable-name-face))
  ;'("^[^ #].*" . font-lock-variable-name-face)) ; more extreme hilight
  "Minimal highlighting for evennia ev files."
  )  

; Auto-indentation 
(defun evennia-indent-line ()
  "Indent current line as batch-code"
  (interactive)
  (beginning-of-line)
  (if (looking-at "^ *#") ; a comment line
      (indent-line-to 0)
    (progn
      (forward-line -1) ; back up one line 
      (if (looking-at "^ *#") ; previous line was comment
          (progn
            (forward-line)
            (indent-line-to 0))
        (progn
          (forward-line)
          (indent-line-to 1)))))
  )

; Register with Emacs system 
(defun evennia-mode ()
  "Major mode for editing Evennia batch-command files."
  (interactive)
  (kill-all-local-variables)
  (use-local-map evennia-mode-map)
  (set (make-local-variable 'indent-line-function) 'evennia-indent-line)
  (set (make-local-variable 'font-lock-defaults) '(evennia-font-lock-keywords))
  (setq major-mode 'evennia-mode)
  (setq mode-name "evennia")
  (run-hooks 'evennia-mode-hook)
)

(provide 'evennia-mode)