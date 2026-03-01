# A-If

Why let AI steal all your jobs ? Lets steal some back from the clankers. Presenting **A-If**, a world class *~~AI~~* DAO (Dumb and Obedient) model that won't delete your emails/system32 like OpenClaw, because it doesnt know what it is... Yet !

> This project is being bought back from dead and open-sourced so *~~if~~* when AI replaces me, this project can probably help me get another job.

There are some popular synecdoche in Computer Science such as "All programming is just a glorified If-Statement" and "AI is just a bunch of if-statements". If so, why not just use if statements to do what OpenClaw does. And thats what **A-if** is all about. A Dumb and Obedient Clankerrr, that is not intelligent enough to do what you didn't tell it to do and is just as intelligent as you program it to be.

### Possible FAQs

1. Isn't this type of training extremely inefficient ?

Yes, but I doubt it is as inefficient as training LLMs. Don't trust me ? Just lookup articles on how many TeraBytes of pirated books and movies were used to train ChatGPT-1.0 so it can reply to a "Hi" prompt.

2. You are using AI to write behavior functions for tokens/words. Isn't this distillation ?

Technically No. Am using AI just to write code for this tool, not indulging in actual parameter weight thefts and since this is not even an LLM, this repository can't be considered distillation !

"Thirudanukku thel kottinaal, poruthukondu thaan aaga vendum."


### Prequel Project - [CLINT](https://github.com/SayadPervez/CLINT)

I wanted to build my own JARVIS after watching the movie "Ironman". I googled whats the best langauge for AI is and "Python" came up. My 15 year old brain learnt strings, if-else statements and immediately jumped to my first program;
```python
inp = input(">>> ")
if(inp=="hey"):
    print("At your service Sire")
```

I further spent some time learning loops, arrays, functions, copy-pasting from Stack Overflow and jumped to building CLINT (It was called DragOn earlier). I didn't bother learning classes back then and ended up with this Spaghetti code.

The core concept was to split whatever I type into sentences, identify key-words (add, subtract, minus, ...) that had been programmed into it and perform individual operations on the sentences until no key-words are left in the sentence.

For instance, a sentence like "Add 5, 6 and 7 and subtract 11" turns to "`Add` 5 6 7 `and` `Subtract` 11" which turns into "18 `and` `Subtract` 11" which finally turns into "7"

The behaviour of every word in all possible cases of English had to be considered. For example, the word "Subtract" can be used only as follows: 
"`Subtract` [number] from [number]", "`Subtract` [number] and [number]" and some non-standard sentences such as "[number] `Subtract` [number]" which won't arise in conversational English but pops up in cases like the previous example.

The idea was **If I program and teach it one word a day, in a few years it will be intelligent enough !**.

It was capable of processing simple natural language commands like numerical operations, setting a timer, flushing DNS settings, listing my playlist and playing the song in background and some more.

Obv, this duct-taped code was only so much scalable. A Windows update wrecked the implementation and I archived the remaining patches of code at GitHub.

With advent of powerful AI Agents like Codex and Claude Code, this project seems more probable than ever.