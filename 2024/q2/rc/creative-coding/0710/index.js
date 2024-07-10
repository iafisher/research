const TEXT = "Through the battered century of world wars and massive violence by other means, there "
    + "had always been an undervoice that spoke through the cannon fire and ack-ack and that "
    + "sometimes grew strong enough to merge with the battle sounds. It was the struggle between "
    + "the state and secret groups of insurgents, state-born, wild-eyed—the anarchists, terrorists, "
    + "assassins and revolutionaries who tried to bring about apocalyptic change. And sometimes of "
    + "course succeeded. The passionate task of the state was to hold on, stiffening its grip and "
    + "preserving its claim to the most destructive power available. With nuclear weapons this power "
    + "became identified totally with the state.";

function encrypt(text, cipher) {
    let r = [];
    for (const letter of text.toUpperCase()) {
        const t = cipher.get(letter);
        if (t) {
            r.push({ letter: t.letter, decrypted: true, hinted: t.hinted });
        } else {
            r.push({ letter, decrypted: false, hinted: false });
        }
    }
    return r;
}

function encryptString(text, cipher) {
    const array = encrypt(text, cipher);
    return array.map(o => o.letter).join("");
}

// courtesy of https://stackoverflow.com/questions/2450954/
function shuffleArray(array) {
    for (var i = array.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var temp = array[i];
        array[i] = array[j];
        array[j] = temp;
    }
}

// courtesy of https://stackoverflow.com/questions/9862761/
function isLetter(str) {
    return str.length === 1 && str.match(/[a-z]/i);
}

function revealHint() {
    const candidates = [];
    for (const [key, value] of USER_CIPHER.entries()) {
        if (value === null && ENCRYPTED.indexOf(key) !== -1) {
            candidates.push(key);
        }
    }

    if (candidates.length === 0) {
        return;
    }

    const index = Math.floor(Math.random() * candidates.length);
    const hint = candidates[index];
    for (const [key, value] of ORIGINAL_CIPHER.entries()) {
        if (key === hint) {
            USER_CIPHER.set(value.letter, { letter: key, hinted: true });
            break;
        }
    }
}

const CipherSettingsView = {
    view: function (vnode) {
        const x = vnode.attrs.value;
        return m("label", [vnode.attrs.key, m("input", {
            disabled: x ? x.hinted : false,
            onchange: function (event) {
                USER_CIPHER.set(vnode.attrs.key, { letter: event.target.value.toUpperCase().trim(), hinted: false });
            }, value: x ? x.letter : ""
        })]);
    }
};

const CipherSettingsBoxView = {
    view: function () {
        const r = [];
        USER_CIPHER.forEach((value, key) => {
            r.push(m(CipherSettingsView, { key, value }));
        });
        return m("div.cipher", r);
    }
};

const EncryptedView = {
    view: function () {
        const letters = encrypt(ENCRYPTED, USER_CIPHER);
        return m("div.encrypted-text",
            letters.map(o => m("span", { class: (o.decrypted ? "decrypted" : "encrypted") + " " + (o.hinted ? "hinted" : "") }, o.letter)));
    }
};

function mostCommonNGrams(text, n) {
    const ngrams = new Map();
    for (let i = 0; i < text.length - (n - 1); i++) {
        let isAllLetters = true;
        for (let j = 0; j < n; j++) {
            if (!isLetter(text[i + j])) {
                isAllLetters = false;
            }
        }

        if (!isAllLetters) {
            continue;
        }

        const key = text.slice(i, i + n);
        const count = ngrams.get(key) ?? 0;
        ngrams.set(key, count + 1);
    }

    const ngramEntries = Array.from(ngrams.entries());
    ngramEntries.sort((x, y) => y[1] - x[1]);
    return ngramEntries.slice(0, 3);
}

const LetterView = {
    view: function (vnode) {
        let r = "";
        for (const letter of vnode.attrs.letters) {
            const x = USER_CIPHER.get(letter);
            if (!x) {
                r = "";
                break;
            } else {
                r += x.letter;
            }
        }

        if (r === "") {
            return vnode.attrs.letters;
        } else {
            return `${vnode.attrs.letters} => ${r}`;
        }
    }
}

const MostCommonStatView = {
    view: function (vnode) {
        return m("p", [`${vnode.attrs.title}: `, m("ol", vnode.attrs.letters.map(b => m("li", [m(LetterView, { letters: b[0] }), ` (${b[1]})`])))]);
    },
}

const StatsView = {
    view: function () {
        const letters = mostCommonNGrams(ENCRYPTED, 1);
        const bigrams = mostCommonNGrams(ENCRYPTED, 2);
        return m("div.stats", [
            m(MostCommonStatView, { title: "Most common letters", letters }),
            m(MostCommonStatView, { title: "Most common bigrams", letters: bigrams }),
        ]);
    }
};

const ButtonsView = {
    view: function () {
        return m("div.buttons", [m("button", { onclick: revealHint }, "hint")]);
    }
}

const RootView = {
    view: function () {
        return m("div", [m(CipherSettingsBoxView), m(EncryptedView), m(StatsView), m(ButtonsView)]);
    }
};

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const HINTS = new Map();
const ORIGINAL_CIPHER = new Map();
const USER_CIPHER = new Map();

const shuffledLetters = Array.from(LETTERS);
shuffleArray(shuffledLetters);
for (let i = 0; i < LETTERS.length; i++) {
    ORIGINAL_CIPHER.set(LETTERS[i], {letter: shuffledLetters[i], hinted: false});
    USER_CIPHER.set(LETTERS[i], null);
}
const ENCRYPTED = encryptString(TEXT, ORIGINAL_CIPHER);
m.mount(document.body, RootView);
