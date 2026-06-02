((python-base-mode
  . ((eglot-workspace-configuration
      . (:pylsp (:plugins (:jedi (:extra_paths ["./submodules/Archipelago"])
                           :pycodestyle (:maxLineLength 100))))))))
