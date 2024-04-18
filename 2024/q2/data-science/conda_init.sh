#!/bin/bash

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/iafisher/Code/research/2024/q2/data-science/miniconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/iafisher/Code/research/2024/q2/data-science/miniconda3/etc/profile.d/conda.sh" ]; then
        . "/Users/iafisher/Code/research/2024/q2/data-science/miniconda3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/iafisher/Code/research/2024/q2/data-science/miniconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<
