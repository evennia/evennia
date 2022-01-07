title: Into 2022 with thanks and plans
copyrights: Image by <a href="https://pixabay.com/users/tumisu-148124/?utm_source=link-attribution&amp;utm_medium=referral&amp;utm_campaign=image&amp;utm_content=6786741">Tumisu</a> from <a href="https://pixabay.com/?utm_source=link-attribution&amp;utm_medium=referral&amp;utm_campaign=image&amp;utm_content=6786741">Pixabay</a>

---

![2022 getting started](https://www.nafcu.org/sites/default/files/inline-images/2022-blog.png)

I didn't write an end-of-the year summary for 2021, so this first devblog of 2022 will also look back a bit at the past year. It also helps me get used to using this new blog platform I wrote about in the previous post.

## On Evennia 1.0

Speaking of 2021, you may have noticed that there was no new versioned Evennia release last year. Last one was 0.9.5 back in 2020. This may make it seem like little is happening in Evennia-land ... but the fact is that while little has happened in `master` branch over the past year, all the more has been going on in Evennia's `develop` branch - the branch which will become Evennia 1.0.

Now, it's not really so good to have a development branch run so long. This is because in the interim people report errors in `master` branch that has since been resolved in `develop`. It's becoming more and more cumbersome to backport which means that `master` is not getting updated all that much right now.

Post 1.0, I'll likely switch to a faster release cycle, but at least for now, it has been hard to avoid, this is because I'm reworking the entire documentation site alongside the code, with new autodocs and tutorials. Releasing an intermediary version with some sort of mid-way documentation version is just not practical for me. So I hope you can be patient a bit further!

Soonish™, I hope to have finished the code changes needed for 1.0 and then I'll invite adventurous folks to use the branch more extensively while the docs are still in flux.

### So what's still to do for Evennia 1.0?

[This is the current TODO list](https://github.com/evennia/evennia/projects/9).

The big one I'm currently doing is to refactor the `contrib/` folder to have more structure (it has grown organically until now). After this, there are a series of bugs and minor features to do. I will also go back and address the low-hanging `master` branch bugs that haven't already been resolved in `develop`.
Most remaining points are then documentation fixes. Those will be handled in one go as the docs are finalized.

### So ...

I won't/can't commit to a deadline for Evennia 1.0, but I'll keep chipping away at it as fast as I can. If you want things to move quicker you are more than welcome to join the other contributors that have chipped in with PRs over the past year. Check out the TODO list and consider investigating a bug or implementing a feature - some may be pretty straight forward.

### ... some thanks!

A big thanks to those that dropped an encouraing buck in my hat (aka [patreon](https://www.patreon.com/griatch) or with a one-time paypal donation) over the year. Everyone has different economical situations and I hope I've been very clear that noone should feel obligated to pay anything. But those of you that could and did - know that you have my thanks - it's very encouraging.

But - just as big thanks go out to _everyone_ that contributed to Evennia in 2021! "Contribution" means so many things - we have the troopers that contributed code and made PRs (best Hacktoberfest yet!), but also those that dilligently reported bugs and pointed out problems as well as (and this is just as important) were active and helpful in the support chat and github discussion!

You guys make the community, that's all there is to it. Thanks a lot.

Now onward into this new, fresh year and towards that elusive Evennia 1.0 ...
