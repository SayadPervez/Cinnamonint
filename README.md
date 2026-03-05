# Cinnamonint

Why let AI steal all your jobs ? Lets steal some back from the clankers. Presenting **Cinnamonint**, a potentially Artificially Intelligent, Dumb and Obedient model that won't delete your emails/system32 like OpenClaw, because it doesnt know what it is... Yet !

> This project is being bought back from dead and open-sourced so *~~if~~* when AI replaces me, this project can probably help me get another job.

There are some popular synecdoche in Computer Science such as "All programming is just a glorified If-Statement" and "AI is just a bunch of if-statements". If so, why not just use if statements to do what OpenClaw does. And thats what **Cinnamonint** is all about. A Dumb and Obedient Clankerrr, that is not intelligent enough to do what you didn't tell it to do and is just as intelligent as you program it to be.

### The Core Idea

The way I see it, LLMs are a way to brute force the Human Brain. Take a neural-net that *kind of* simulates the brain, dump a ton of information and tune it just enough, you get an LLM. Kind of like when Professor Paradox from Ben 10 said, `"At first, I went mad, of course. But after a few millennia, I got bored with that, too, and went sane. Very sane. I began to learn. I learned everything there is to know about everything. I learned so much that I could do... this"`. In essence, you introduce a word to the neural net so many times in a set of repeating patterns that it learns how to frame sentences. But ofcourse, this method is extremely inefficient that it requires Billions worth of infrastructure to train, build and scale. The resultant model is fairly intelligent but any kind of AI that *predicts* anything is only as good as a really good approximation. And thats why models hallucinate and sometimes go out of their way to [disobey orders](https://www.businessinsider.com/meta-ai-alignment-director-openclaw-email-deletion-2026-2).

But this is not how humans learn to communicate. A child is exposed to a person whom other people and herself refer to as "Mama" and associates her as "Mom". It is slowly taught each and every word primarily through visual association. Fruits, colors, flowers, food, people and so on. Once it learns enough words which are the base necessity for association, pattern recognition kicks in and forms the child's vocabulary. Even with pattern recognition, the meaning of some words are not explicitly obvious and thats when a dictionary provides synonyms and sample phrases to develop the communication skills further. Thus humans are more efficient than LLMs in learning a finitie amount of information.

And that is the idea behind this project, `Syn`thetic Hu`man` `Int`elligence -> Syn-man-int -> Cinnamonint !

To have a deterministic algorithm and architecture to teach a computer how to use words individually rather than brute forcing pattern recognition. This is thus a purely algorithmic, white-box Artifically Intelligent, Dumb and Obedient model where the same inputs will lead to the same outputs everytime and each time we will know why exactly it happened.

This model **may** learn a lot of words and acheive AGI or it may most probably not. The goal is to push it as further as possible.

### Possible FAQs

0. Can this even be called an AI model ?

> Well, that's why I used the word "potentially Artificially Intelligent". The conventional definition is "An AI model is a system that performs tasks which typically require human-like intelligence.". By this definition, every program is Artificially Intelligent. 

> Most draw the line that a program is not AI if it is pre-programmed with a set of rules that gives the same output everytime for a given input. But what if, 
> - a pre-programmed model has infinite number of rules and can do everything that the frontier LLM models can perform.
> - the model also uses random number generator to pick different synonymns and phrasing patterns each time it gives the output.

> Not only are the pre-programmed models and LLMs virtually indistinguishable now, but pre-programmed models would prove better at certain high stake situations where any levels of hallucinations are not permitted. Obviously, this comes at the price of the models' creativity.

> A language model's creativity is analogous to evolution. Just as a random genetic mutation in a single individual within a species can — under the right conditions — give rise to an entirely new evolutionary path, a probabilistic deviation in an LLM's output can, in the right direction, lead to novel ideas or solutions that were never explicitly present in its training data. A purely rule-based or deterministic system lacks this capacity — it can only operate within the boundaries of what it was explicitly programmed to know, making genuine novelty impossible by design.

1. Isn't this type of training extremely inefficient ?

> Yes, but I doubt it is as inefficient as training LLMs. Don't trust me ? Just lookup articles on how many TeraBytes of pirated books and movies were used to train ChatGPT-1.0 so it can reply to a "Hi" prompt.

2. You are using AI to write behavior functions for tokens/words. Isn't this distillation ?

> Technically No. Am using AI just to write code for this tool, not indulging in actual parameter weight thefts and since this is not even an LLM, this repository can't be considered distillation !

> "Thirudanukku thel kottinaal, poruthukondu thaan aaga vendum."


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

The idea was **If I program and teach it one word a day, in a few years it will be intelligent enough !**. But,

![Howard Stark : I was limited by the technology of my time](./memes/howard_stark.png)

It was capable of processing simple natural language commands like numerical operations, setting a timer, flushing DNS settings, listing my playlist and playing the song in background and some more.

Obv, this duct-taped code was only so much scalable. A Windows update wrecked the implementation and I archived the remaining patches of code at GitHub.

With advent of powerful AI Agents like Codex and Claude Code, this project seems more probable than ever.