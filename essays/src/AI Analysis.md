---
title: "AI Analysis"
date: 2026-08-31
category: philosophy
deck: "On entropy, redundant bits, and why a five-word text beats a five-page essay at fooling the detector"
---

Can you identify if something is written by AI?

This is not one of those AI-generated articles that have a silly hook and then move into shilling an AI product. I recently had a report at my university return with AI-generated content and was asked to rewrite a few sections, when I checked with the AI detecting applications, it returned that the section contained "Straightforward structure and technical jargon". Hmmm, what else would we expect from a reflective report on engineering training, a task *famous* for technical jargon?

A lot of the sentence structures noticed in AI are derived from its training data - and believe it or not, before 2022, people who write or at least considered themselves half-decent at writing, used to write *without AI*, and that is what the AI has been trained on (by early 2025, 35% of the websites uploaded to the internet are AI-generated or assisted [1]) - which would mean its just a probabilistic (read: slightly worse) version of what humans actually write, and guess who is also a slightly less refined version of functioning professionals/academics? The answer is teenagers and undergraduate students.

Let's leave that aside and let me tell you about something (not very nice) that I did. I have a bunch of Instagram and WhatsApp chats with my friends (around 1000 - 4000 texts per person, about 20 people), and I used that data to train an LLM to reply as me (this is quite easy with the APIs and models available nowadays, very plug and play - you can even train a model on your voice in less than 30 seconds), to them, and plugged it into my dms.

Not a single person said anything, even if they realised, and I would say it is quite likely that they *didn't* realise, considering the average text length between my friends and I is 5 words, and the most commonly used word is 'bruh'.

I also rewrote a book review with AI (about 3 pages or so) and everyone I asked to critique told me that while the content seems fine, the writing very clearly feels AI-generated. Well, let me see what I did different here - I gave about a 1 page word-dump mentioning my thoughts and insights of the book to the AI, provided it a few references of my actual writing and asked it to go fill up the book review word requirement, where it goes from 1 page to 3.

So this would mean a 5-word text message between friends is likely not to be identified as AI written, while a 5 page essay would be...
AI is apparently better at taking over the fun part of the job.

Now, this may be where we start to get into some trouble, and I would like to call upon some principles from Claude Shannon's Information Theory. If transmitting a message, there are redundant bits, removing which you can still infer the original meaning of a message (paraphrased, of course).
This is the general principle behind being able to successfully compress anything - from pdfs, jpegs to all communication on the internet and elsewhere. Your non-redundant information in the original word dump is ~70% of a page (I'm assuming for the better here), and the AI - which has been politely asked not to hallucinate and make up false information, must flub and pull ideas from its training data on the book and writing principles and similar books *yada yada* - its diluting the core message, while not adding any non-redundant bits. When an academic detailing his theory fills up that flub area that he must, he inserts anecdotal evidence, bits of his personality, and sometimes irrelevant information - their complaints on the current financial climate, for instance - (back in 2010, a physics paper wrote "The authors would like to thank Lehman Brothers for blocking our research funds and forcing us to spend months restructuring our entire laboratory budget instead of solving the field equations."[2]).

We further expect general human writing to have higher *entropy* than AI writing (how unpredictable the next word in the sentence would be), because the AI goes down a statistically predictable path.

If I were a real academic I would pose the question, at what limit do you become perceptible to this AI generated content? 20 words, 500 words or maybe 50 pages. This limit is likely not constant, and as models keep getting better this limit is likely going to keep getting pushed further and further. Maybe a new diffusion model comes out and this article is completely irrelevant in two months. But I am not an academic, and I am satisfied with simply publishing my thoughts and going on my day, treating this like the grievances column of The Times.

### References

[1] arXiv preprint arXiv:2604.26965 (2026). _The Impact of AI-Generated Text on the Internet_. Available at: [https://arxiv.org/abs/2604.26965](https://arxiv.org/abs/2604.26965)
[2] Anonymous / Math & Physics Preprint Acknowledgments (c. 2010-2011). _"A Note on Complexities of Certain Topology Problems"_.
