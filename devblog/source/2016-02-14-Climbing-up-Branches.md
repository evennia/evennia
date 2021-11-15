[![](https://2.bp.blogspot.com/-YRSejcCHpq4/VsDcZRdmTVI/AAAAAAAAEgE/oK4igrEnqWk/s320/male-lazuli-bunting-bird-perches-on-branch-passerina-amoena.jpg)](https://2.bp.blogspot.com/-YRSejcCHpq4/VsDcZRdmTVI/AAAAAAAAEgE/oK4igrEnqWk/s1600/male-lazuli-bunting-bird-perches-on-branch-passerina-amoena.jpg)

Today I pushed the latest Evennia development branch "wclient". This has a bunch of updates to how Evennia's webclient infrastructure works, by making all exchanged data be treated equal (instead of treating text separately from other types of client instructions).  
  
It also reworks the javascript client into a library that should be a lot easier to expand on and customize. The actual client GUI is still pretty rudimentary though, so I hope a user with more web development experience can take upon themselves to look it over for best practices.  
  
A much more detailed description of what is currently going on (including how to check out the latest for yourself) is found in this [mailing list post](https://groups.google.com/forum/#!category-topic/evennia/evennia-news/xWQu_YVm14k). Enjoy!