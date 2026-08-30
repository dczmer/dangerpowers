# Confidence Intervals (Wilson Score), ELI5

> **Disclaimer:** This document was entirely AI-generated, but fact-checked by me against Wikipedia. I used this to get the basic idea of this concept when I encountered it while researching trigger testing. It is included here because I liked the explanation, and it's relevant info for our discussion on trigger testing and sampling results. Also, the fence analogy plus the name "Wilson" reminds me of Home Improvement.

**Prompt that generated this:**

> i know nothing about statistics and my math skills are weak. explain wilson score intervals to me like i'm a 5 year old. https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval use analogies and visual aids to explain complex concepts.

---

# Wilson Score Intervals, Explained with Cookies 🍪

## The Big Question

Imagine there's a giant jar with **thousands** of cookies. Some cookies are yummy, some are yucky. You want to know: *"What fraction of cookies are yummy?"*

But you can't eat all the cookies. You can only taste a few.

So the real question becomes: **"I tasted some cookies... how sure can I be about the whole jar?"**

---

## Step 1: The Silly Answer (just use the fraction!)

You taste 10 cookies. 7 are yummy. You say:

```
"TASTED: 🍪🍪🍪🍪🍪🍪🍪🤢🤢🤢
 → 7/10 = 70% of ALL cookies must be yummy!"
```

That's a bit **overconfident**. You only tasted 10! Maybe you got lucky.

---

## Step 2: The "Fuzzy Range" Idea (confidence interval)

A smarter kid says: *"I'm pretty sure the true yummy-fraction is somewhere in a **range**, like between 40% and 90%."*

```
0%        40%    70%    90%        100%
 |---------[=====👍=====]----------|
           "the true answer
            is probably in here"
```

That range is called a **confidence interval**. It's like saying *"the answer is hiding in this fenced area."* A **95%** interval means: if you played this tasting game 100 times, your fence would catch the true answer about 95 times.

---

## Step 3: The Old, Broken Fence (the "Wald" method)

The old way to build the fence was:

> **"Take your fraction, then add a little bit on each side, same size both ways."**

```
        70% ← your guess
   [----+--------|--------+----]
        ← 20%  →    ← 20%  →     (same padding both sides)
```

This works OK **if you taste LOTS of cookies**. But it breaks in two silly ways:

### Break #1: The fence falls off the number line! 🙈

You taste 3 cookies. All 3 are yummy. The old method says:

```
guess = 100%, padding = 10%
0%                    100%  110% ← ??? 
 |---------------------[=====|==]──┤
                     "110% yummy"?? That's impossible!
```

You can't have 110% of cookies be yummy. The fence goes past the edge of reality!

### Break #2: The fence shrinks to nothing! 🔬

If all 3 cookies are yummy, the old formula computes padding = **zero**, and confidently declares:

```
"THE ANSWER IS EXACTLY 100%. I AM CERTAIN."
                          ↑
                    (after tasting THREE cookies!)
```

That's obviously nonsense. You just got lucky!

---

## Step 4: Wilson to the Rescue! 🦸

A clever man named **Wilson** (in 1927!) built a better fence with two magic tricks:

### Magic Trick #1: "Pretend you saw a few extra, boring cookies" 🍪➕

Wilson says: *"Before you brag, pretend you tasted 4 extra cookies: 2 yummy, 2 yucky."* (This is called the **"plus four"** rule, and it's a shortcut version of Wilson's method.)

```
REAL cookies:    🍪🍪🍪🤢         (3 out of 4 yummy → 75%)
+ FAKE cookies:  🍪🍪🤢🤢         (Wilson's imaginary cookies)
─────────────────────────────
"ADJUSTED" guess: (3+2) out of (4+4) = 5/8 ≈ 63%
```

The fake cookies **gently tug your guess toward the middle (50%)**, like a bungee cord pulling you toward safety:

```
0%          50%  63%      75%     100%
 |-----------[===👈=======●]-------|
              bungee pulls
              you off the edge
```

**Why is this smart?**
- If you've only tasted 4 cookies, the 4 fake cookies have a big effect — the pull is **strong** (you should be humble!).
- If you've tasted 4,000 cookies, 4 fake cookies are nothing — the pull is **tiny** (you've earned your confidence!).

### Magic Trick #2: "The fence can be lopsided" ⚖️

Wilson's fence doesn't have to be equal on both sides. Near the edges of the number line, it squishes:

```
Near an edge (95% yummy):
0%                    [==|======] 100%
                       squished     ← can't cross 100%,
                       on this      so it stretches
                       side         the other way!
```

**It never, ever goes below 0% or above 100%.** The fence stays inside reality.

---

## Side-by-Side Picture 📊

Tasting 3 cookies, all yummy:

```
OLD (Wald) fence:   "Exactly 100%. Trust me."
                    ───────────────● (zero width, nonsense)

WILSON fence:       "Somewhere between ~44% and 100%."
                    0%        [====|============] 100%
                    honest about small samples! ✅
```

Tasting 1,000 cookies, 950 yummy:

```
WILSON fence:       [====|====]  ← narrow, because lots of
                    evidence! ✅
```

---

## Why Does This Matter in Real Life?

Websites use Wilson intervals to **rank reviews** fairly. Imagine two products:

```
Product A: 5 stars from 2 people      → 100% 🌟🌟
Product B: 4.8 stars from 1,000 people → 96% 🌟🌟🌟...🌟
```

Raw percentages say A wins. But Wilson says: *"Product A only has 2 reviews — I'm not sure about it at all. Product B has tons of evidence."* Wilson's fence for A is huge, and its **bottom edge** (the worst it could plausibly be) is low. So B ranks higher. That's why Reddit and others sort comments using **the bottom of the Wilson interval** — it's the "I'm confident it's at least THIS good" score.

---

## TL;DR 🎯

> When you only get a few tries, don't brag about the exact fraction. Wilson's trick:
> 1. **Add a few imaginary 50/50 results** to stay humble when evidence is scarce,
> 2. Let the fence be **lopsided** so it never falls off the 0%–100% number line,
> 3. The more data you have, the less it adjusts — **it grows up with you.**

If you ever need to compute one, you don't need the scary formula from the Wikipedia page — free calculators online do it, and the "+4 rule" (`(successes+2)/(total+4)`) gets you most of the way there. 🍪
