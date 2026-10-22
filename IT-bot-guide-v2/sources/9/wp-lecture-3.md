<!-- p1 -->
Web Programming
Cascading Style Sheet (CSS)
– 1 –
Dr. Eva Hriekes
Email: evahriekes@gmail.com
<!-- p2 -->
Lecture Outline
What is CSS?
CSS Syntax
Location of Styles
Selectors
<!-- p3 -->
Section 1 of 4
WHAT IS CSS?
<!-- p4 -->
What is CSS(Cascading Style Sheet)?

CSS is a W3C standard for describing the presentation (or appearance)
of HTML elements.

With CSS, we can assign
font properties
colors
sizes
borders
background images
position of elements

CSS is a language in that it has its own syntax rules.

CSS can be added directly to any HTML element (via the style attribute),
within the <head> element, or most commonly, in a separate text file
that contains only CSS.
<!-- p5 -->
Benefits of CSS

Why using CSS is a better way of describing presentation than HTML?
The degree of formatting control in CSS is significantly better than
that provided in HTML.
Web sites become significantly more maintainable because all
formatting can be centralized into one, or a small handful of CSS
files.
A site built using a centralized set of CSS files for all presentation will
also be quicker to download because each individual HTML file will
contain less markup.
CSS can be used to adopt a page for different output mediums.
<!-- p6 -->
<!-- fig: figs/wp-lecture-3-p6.jpg -->
CSS Versions
version
year
CSS 1
1996
CSS 2
1998
CSS 2.1
2011
CSS 3
-
Taxonomy and status of CSS3 modules
●Recommendation ●Candidate Recommendation
●Working Draft.
<!-- p7 -->
Section 2 of 4
CSS SYNTAX
<!-- p8 -->

A CSS document consists of one or more style rules.

A rule consists of a selector that identifies the HTML element or
elements that will be affected, followed by a series of property and
value pairs (each pair is also called a declaration).
selector { property: value; property2: value2; }
declaration block
declaration
em { color: red; }
p {
     margin: 5px 0 10px 0;
     font-weight: bold;
     font-family: Arial, Helvetica, sans-serif;
}
property
value
selector
rule
syntax
examples
CSS Syntax
Rules, properties, values, declarations
<!-- p9 -->
Declaration Blocks

The series of declarations is also called the declaration block.
A declaration block can be together on a single line, or spread across
multiple lines.
The browser ignores white space.
Each declaration is terminated with a semicolon.
selector { property: value; property2: value2; }
declaration block
declaration
em { color: red; }
p {
     margin: 5px 0 10px 0;
     font-weight: bold;
     font-family: Arial, Helvetica, sans-serif;
}
property
value
selector
rule
syntax
examples
<!-- p10 -->
Properties

Each individual CSS declaration must contain a property.

These property names are predefined by the CSS standard.

The CSS2.1 Recommendation
defines over a hundred
different property names.
selector { property: value; property2: value2; }
declaration block
declaration
em { color: red; }
p {
     margin: 5px 0 10px 0;
     font-weight: bold;
     font-family: Arial, Helvetica, sans-serif;
}
property
value
selector
rule
syntax
examples
<!-- p11 -->
Property Type
Property
Fonts
font
font-family
font-size
font-style
font-weight
Font-variant
@font-face
Text
letter-spacing
line-height
text-align
text-decoration
text-indent …. etc
Color and background
background
background-color
background-image
background-position
background-repeat
color
Borders
border
border-color
border-width
border-style
border-top
border-top-color
border-top-width ….. etc
Properties
Common CSS properties
<!-- p12 -->
Property Type
Property
Spacing
padding
padding-bottom, padding-left, padding-right, padding-top
margin
margin-bottom, margin-left, margin-right, margin-top
Sizing
height
max-height
max-width
min-height
min-width
width
Layout
bottom, left, right, top
clear
display
float
overflow
position
visibility
z-index
Lists
list-style
list-style-image
list-style-type
Properties
Common CSS properties continued
<!-- p13 -->

Each CSS declaration also contains a value for a property.

Some property values are from a predefined list of keywords.

Others are values such as length measurements, percentages, numbers
without units, color values, and URLs.

The unit of any given value is dependent upon the property.
Values
What style value for the properties
<!-- p14 -->
Color Values
CSS supports a variety of different ways of describing color
Methods
Description
Example
Name
Use one of 17 standard color names. CSS3 has 140
standard names.
color: red;
color: hotpink; /* CSS3 only */
RGB
Uses three different numbers between 0 and 255 to
describe the Red, Green, and Blue values for the
color.
color: rgb(255,0,0);
color: rgb(255,105,180);
Hexadecimal
Uses a six-digit hexadecimal number to describe the
red, green, and blue value of the color; each of the
three RGB values is between 0 and FF.
color: #FF0000;
color: #FF69B4;
RGBa
Allows you to add an alpha, or transparency, value
which is between 0.0 (fully transparent) and 1.0
(fully opaque).
color: rgb(255,0,0, 0.5);
HSL
Allows you to specify a color using Hue, Saturation
and Light values.
color: hsl(0,100%,50%);
color: hsl(330,59%,100%);
<!-- p15 -->
Units of Measurement

There are multiple ways of specifying a unit of measurement in CSS:

relative units, specify a length relative to another length property.

absolute units, are fixed and a length expressed in any of these will
appear as exactly that size.
Unit
Description
Type
px
Pixel (1/96 of an inch).
Relative  (CSS2)
Absolute (CSS3)
em
Equal to the computed value of the font-size property of
the element on which it is used. When used for font sizes,
the em unit is in relation to the font size of the parent.
Relative
%
A measure that is always relative to another value.
Relative
rem
Stands for root em, it is relative to font-size of the root
element.
Relative (CSS3 only)
in
Inches  (1in = 96px = 2.54cm)
Absolute
cm
Centimeters
Absolute
mm
Millimeters
Absolute
pt
Points (equal to 1/72 of an inch)
Absolute
pc
Pica (equal to 1/6 of an inch)
Absolute
<!-- p16 -->
Units of Measurement Example1
<head>
<style>
p { font-size: 16px;
line-height: 2em; }
div { font-size: 30px;
border: 1px solid black; }
span { font-size: 0.5em; }
</style>
</head>
<body>
<p> This paragraph has a calculated <br> line-height of: 2 x 16px = 32px.</p>
<div> The font-size of the div element is set to 30px.
<span> The span element inside the div element has a font-size of 0.5em, which
equals to 0.5 x 30 = 15px </span>.
</div>
</body>
<!-- p17 -->
Units of Measurement Example2
<head>
<style>
body { font-size:16px; }
div {
font-size: 150%;
border: 1px solid black; }
</style>
</head>
<body>
<p> The font-size of this document is 16px. </p>
<div> The font-size of this div element is 150%. </div>
<p> The % unit sets the font-size relative to the current font-size. </p>
</body>
<!-- p18 -->
Units of Measurement Example3
<head>
<style>
html { font-size: 16px; }
div { font-size: 2rem;
border: 1px solid black; }
</style>
</head>
<body>
<p> The font-size of this document is 16px. </p>
<div> The font-size of this div element is 2rem. It shows that it does not inherit
from
its parent element font size. </div>
<p> The rem unit sets the font-size relative to the browsers base font-size, and will
not inherit from its parents.</p>
</body>
<!-- p19 -->
Examples

Enclose multi-word font names in quotes
This paragraph uses the first style above.
This h2 uses the second style above.
output
p {
font-family: Georgia;
}
h2 {
font-family: "Courier New";
}
CSS
<!-- p20 -->
Examples
p {
font-weight: bold;
font-style: italic;
}
CSS
This paragraph uses the style above.
output
blockquote { text-align: justify; }
h2 { text-align: center; }
CSS
The Gollum’s Quote
We wants it, we needs it. Must have the precious. They stole it from us.
Sneaky little hobbitses. Wicked, tricksy, false!
output
<!-- p21 -->
Examples
p {
text-decoration: underline;
}
CSS
This paragraph uses the style above.
output
body {
background-image: url("images/draft.jpg");
}
CSS
<!-- p22 -->
Examples
body {
background-image: url("images/draft.jpg");
background-repeat: no-repeat;
background-position: 370px 20px;
}
CSS
<!-- p23 -->
Examples
p {
color: red;
background-color: yellow;
}
CSS
This paragraph uses the style above                                                        output
p { color: red; }
h2 { color: rgb(128, 0, 196); }
h4 { color: #FF8800; }
CSS
This paragraph uses the first style above
This h2 uses the second style above.
This h4 uses the third style above.
output
<!-- p24 -->
Comments in CSS

It is often helpful to add comments to your style sheets.

Comments take the form: /* comment goes here */

Ex:
/* This is a comment.
It can span many lines in the CSS file. */
p {
color: red;
background-color: aqua;
}
<!-- p25 -->
Section 3 of 4
LOCATION OF STYLES
<!-- p26 -->
Types of Style Sheet

Actually there are three Different types of style sheet:
Author-created style sheets (what we are learning in this
presentation).
User style sheets allow the individual user to tell the browser to
display pages using that individual’s own custom style sheet. This
option is available in a browser usually in its accessibility options
area.
The browser style sheet defines the default styles the browser uses
for each HTML element.
<!-- p27 -->
Style Locations

CSS style rules can be located in three different locations:

Inline

When style is used for only one HTML element

Embedded
When style sheet is used for only one web page

External
Many pages can be linked to a single style sheet
Changes to style sheet will change the appearance of all web pages
linked to it

You can combine all 3!
<!-- p28 -->
Inline Styles

Style rules placed within an HTML element via the style attribute.

An inline style only affects the element it is defined within and will
override any other style definitions for the properties used in the inline
style.

Using inline styles is generally discouraged since they decrease
maintainability.
<h1> Share Your Travels </h1>
<h2 style="font-size: 24pt"> Description </h2>
...
<h2 style="font-size: 24pt; font-weight: bold;"> Reviews </h2>
<!-- p29 -->
Embedded Style Sheet

Style rules placed within the <style> element inside the <head> element

Since each HTML document has its own <style> element, it is more
difficult to consistently style multiple documents when using embedded
styles.
<head lang="en">
<meta charset="utf-8">
<title>Share Your Travels -- New York - Central Park</title>
<style>
h1 { font-size: 24pt; }
h2 {
font-size: 18pt;
font-weight: bold;   }
</style>
</head>
<body>
<h1>Share Your Travels</h1>
<h2>New York - Central Park</h2>
...
<!-- p30 -->
External Style Sheet

Style rules placed within a external text file with the .css extension

This is by far the most common place to locate style rules because it
provides the best maintainability.

When you make a change to an external style sheet, all HTML documents that
reference that style sheet will automatically use the updated version.

The browser is able to cache the external style sheet which can improve the
performance of the site
<head lang="en">
<meta charset="utf-8">
<title>Share Your Travels -- New York - Central Park</title>
<link rel="stylesheet" href="styles.css" />
</head>
<!-- p31 -->
Section 4 of 4
SELECTORS
<!-- p32 -->
Selectors

When defining CSS rules, you will need first to use a selector to tell the
browser which elements will be affected.

CSS selectors allow you to select:

Individual elements

Multiple HTML elements

Elements that belong together in some way

Elements that are positioned in specific ways in the document
hierarchy

There are a number of different selector types.
<!-- p33 -->

Uses the HTML element name.

You can select all elements by using the universal element selector,
which is the * (asterisk) character.

Ex:
p {
margin: 5px 0 10px 0;
font-weight: bold;
font-family: Arial, Helvetica, sans-serif;
}
* { color: red; }
Element Selectors
Selects all instances of a given HTML element
<!-- p34 -->

You can select a group of elements by separating the different element
names with commas.
/* commas allow you to group selectors */
p, div, h1 {  margin: 0;
padding: 0;
}
/* the above single grouped selector is equivalent to the following: */
p {  margin: 0;
padding: 0;
}
div {  margin: 0;
padding: 0;
}
h1 {  margin: 0;
padding: 0;
}
Grouped Selectors
Selecting multiple things
<!-- p35 -->

A class selector allows you to simultaneously target different HTML
elements regardless of their position in the document tree.

If a series of HTML element have been labeled with the same class
attribute value, then you can target them for styling by using a class
selector, which takes the form: period (.) followed by the class name.

If we don’t specify an element, the class name applies to all the
elements
Class Selectors
Simultaneously target different HTML elements
.first {
font-style: italic;
color: brown;
}
CSS
<p class = "first">class selector</p>
<h1 class = "first" > element</h1>
HTML
<!-- p36 -->
<head>
<title>Share Your Travels </title>
<style>
.first {
font-style: italic;
color: brown;
}
</style>
</head>
<body>
<h1 class="first">Reviews</h1>
<div>
<p class="first">By Ricardo on
<time>September 15, 2012 </time>
</p>
<p>Easy on the HDR buddy.</p>
</div>
<hr/>
<div>
<p class="first">By Susan on
<time>October 1, 2012</time>
</p>
<p>I love Central Park.</p>
</div>
<hr/>
</body>
.first {
   font-style: italic;
   color: brown;
}
Class Selectors
Example
<!-- p37 -->
<head>
<style>
p.error {
color: red;
}
</style>
</head>
<body>
<p>This is a paragraph.</p>
<p>This is a paragraph.</p>
<p class="error">I am different.</p>
<p>This is a paragraph.</p>
<p class="error">I am different too.</p>
</body>
This is a paragraph.
This is a paragraph.
I am different.
This is a paragraph.
I am different too
Class Selectors
Example
<!-- p38 -->

An id selector allows you to target a specific element by its id attribute
regardless of its type or position.

If an HTML element has been labeled with an id attribute, then you can
target it for styling by using an id selector, which takes the form:
pound/hash (#) followed by the id name.

Note: You should only be using an id once per page.
Id Selectors
Target a specific element by its id attribute
<!-- p39 -->
<head lang="en">
<meta charset="utf-8">
<title>Share Your Travels -- New York - Central Park</title>
<style>
#latestComment {
font-style: italic;
color: brown;
}
</style>
</head>
<body>
<h1>Reviews</h1>
<div id="latestComment">
<p>By Ricardo on
<time>September 15, 2012</time></p>
<p>Easy on the HDR buddy.</p>
</div>
<hr/>
<div>
<p>By Susan on <time>October 1, 2012</time></p>
<p>I love Central Park.</p>
</div>
<hr/>
</body>
#latestComment {
   font-style: italic;
   color: brown;
}
Id Selectors
Example
<!-- p40 -->

An attribute selector provides a way to select HTML elements by either
the presence of an element attribute or by the value of an attribute.

Attribute selectors can be a very helpful technique in the styling of
hyperlinks and images.
Attribute Selectors
Selecting via presence of element attribute or by the value of an attribute
<!-- p41 -->
<head lang="en">
<meta charset="utf-8">
<title>Share Your Travels</title>
<style>
[title] {
cursor: help;
padding-bottom: 3px;
border-bottom: 2px dotted blue;
text-decoration: none;
}
</style>
</head>
<body>
<div>
<img src="images/flags/CA.png" title="Canada Flag" />
<h2><a href="countries.php?id=CA" title="see posts from Canada">
Canada</a>
</h2>
<p> Canada is a North American country consisting of … </p>
<div>
<img src="images/square/6114907897.jpg" title="At top of Sulpher Mountain">
<img src="images/square/6592317633.jpg" title="Grace Presbyterian Church">
<img src="images/square/6592914823.jpg" title="Calgary Downtown">
</div>
</div>
</body>
[title] {
   cursor: help;
   padding-bottom: 3px;
   border-bottom: 2px dotted blue;
   text-decoration: none;
}
Attribute Selectors
Example
<!-- p42 -->

Some of the most common ways one can construct attribute selectors in
CSS3.
Attribute Selectors
Selecting via presence of element attribute or by the value of an attribute
Selector
Matches
Example
[]
A specific attribute.
[title]
Matches any element with a title attribute
[=]
A specific attribute with a specific value.
a[title="posts from this country"]
Matches any <a> element whose title attribute is exactly
"posts from this country"
[~=]
A specific attribute whose value matches
at least one of the words in a spaced
delimited list of words.
[title~="Countries"]
Matches any title attribute that contains the word
"Countries"
[^=]
A specific attribute whose value begins
with a specified value.
a[href^="mailto"]
Matches any <a> element whose href attribute begins
with "mailto"
[*=]
A specific attribute whose value contains
a substring.
img[src*="flag"]
Matches any <img> element whose src attribute contains
somewhere within it the text "flag"
[$=]
A specific attribute whose value ends
with a specified value.
a[href$=".pdf"]
Matches any <a> element whose href attribute ends with
the text ".pdf"
<!-- p43 -->

A pseudo-element selector is a way to select something that does not
exist explicitly as an element in the HTML document tree but which is
still a recognizable selectable object.

A pseudo-class selector does apply to an HTML element, but targets
either a particular state or, in CSS3, a variety of family relationships.

The most common use of this type of selectors is for targeting link
states.
Pseudo Selectors
Select something that does not exist explicitly as an element
<!-- p44 -->
Pseudo-Class and Pseudo-Element Selectors
Selector
Type
Description
a:link
pseudo-class
Selects links that have not been visited
a:visited
pseudo-class
Selects links that have been visited
:focus
pseudo-class
Selects elements (such as text boxes or list boxes) that have the
input focus.
:hover
pseudo-class
Selects elements that the mouse pointer is currently above.
:active
pseudo-class
Selects an element that is being activated by the user. A typical
example is a link that is being clicked.
:checked
pseudo-class
Selects a form element that is currently checked. A typical
example might be a radio button or a check box.
:first-child
pseudo-class
Selects an element that is the first child of its parent. A common
use is to provide different styling to the first element in a list.
:first-letter
pseudo-element
Selects the first letter of an element. Useful for adding drop-caps
to a paragraph.
:first-line
pseudo-element
Selects the first line of an element.
<!-- p45 -->
Pseudo Selectors
Example
<head>
<title>Share Your Travels</title>
<style>
a:link {
text-decoration: underline;
color: blue;
}
a:visited {
text-decoration: underline;
color: purple;
}
a:hover {
text-decoration: none;
font-weight: bold;
}
a:active {
background-color: yellow;
}
</style>
</head>
<body>
<p>Links are an important part of any web page. To learn more about
links visit the <a href="#">W3C</a> website.</p>
<nav>
<ul>
<li><a href="#">Canada</a></li>
<li><a href="#">Germany</a></li>
<li><a href="#">United States</a></li>
</ul>
</nav>
</body>
<!-- p46 -->

A contextual selector (in CSS3 also called combinators) allows you to
select elements based on their ancestors, descendants, or siblings.

It selects elements based on their context or their relation to other
elements in the document tree.
Selector
Matches
Example
Descendant
A specified element that is contained
somewhere
within
another
specified
element
div p
Selects a <p> element that is contained somewhere within
a <div> element. That is, the <p> can be any descendant, not
just a child.
Child
A specified element that is a direct
child of the specified element
div>h2
Selects an <h2> element that is a child of a <div> element.
Adjacent Sibling
A specified element that is the next
sibling (i.e., comes directly after) of the
specified element.
h3+p
Selects the first <p> after any <h3>.
General Sibling
A specified element that shares the
same parent as the specified element.
h3~p
Selects all the <p> elements that share the same parent as the
<h3>.
Contextual Selectors
Select elements based on their ancestors, descendants, or siblings
<!-- p47 -->

A descendant selector matches all elements that are contained within
another element. The character used to indicate descendant selection is
the space character.
div  p { … }
context
selected element
Selects a <p> element
somewhere
within a <div> element
#main div p:first-child { … }
Selects the first <p> element
somewhere within a <div> element
that is somewhere within an element
with an id="main"
Descendant Selector
Selects all elements that are contained within another element
<!-- p48 -->
<!-- fig: figs/wp-lecture-3-p48.jpg -->
Contextual Selectors in Action
