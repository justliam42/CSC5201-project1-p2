# CSC4201 — Mini-Project — Part 2

Albin Berisha, Grant Fisco, Liam Otten, Peli Orugbani
October 2026

---

## Project Instructions

For this (small!) project, you are part of a team that is designing a simple ecommerce application.

You are not responsible for the entire application (at least, not yet!), but you are responsible for one of the
services.
### The Services
Here we are documenting a minimal API for each of the services. For now you are only implementing one
of them, but it may be helpful to see how your service fits into the larger whole.
**Catalog** service provides a listing of the products available on the site. Each product has a product id, name,
textual description, price in US Dollars, and list of categories.
It provides one endpoint (/products)for returning a list of (all) items, with an optional search string
to return only those items whose name or description contains the search string. It also provides an
endpoint (/products/product id) for each individual product.

**Cart** stores each currently-connected user’s cart in a Redis DB. Users are assigned an ID by session, and
do not log in.
It provides a single endpoint (/cart/user id), with GET requests returning the cart contents,
POST adding an item to the cart, and DELETE emptying the cart.

**Payment** Given credit-card information (card number, date, SVN, etc.), validate the card, then (mock)
“charge” it.
It provides a single endpoint where we post charges, passing in both the amount charged, and the card
information. It will return either an error (the card is invalid/expired/declined/etc.) or a transaction id
(randomly-generated UUID for our purposes).

**Shipping** service both provides estimated shipping costs, and (mock) ships orders.
A GET request for /shipping/order id should return the shipping estimate, while a POST of a
valid shipping address triggers the (mock) shipping process.

**Notification** service (mock) sends an email confirming each order.
POST to /emails/user id to send a message.

**Checkout** service will orchestrate other services to (mock) checkout a customer. This can be (mock) triggered by POSTing payment and shipping information to /checkout/user id.

**Recommendation** service returns a list of up to 5 products from the catalog which are recommended based
on the user’s current cart contents.
It has a single endpoint recommendations/user id

**Frontend** service will serve webpages whose content depends on the other services.

---

Endpoints without specified methods are assumed to use GET.
N.B. Many of the services are mock implemented. We are not actually running a store and do not wish
to actually bill credit cards, ship goods, or send email.

---

## Bringing It All Together
While you are in charge of one of the services, your team should manage the entire application. (That is,
part 2 is now a team project.) As individuals you should:
- Modify the configuration of your service in “production” to use the “production” instance of your teammates’ services.  
  
In addition, the team should:  
- Implement the Checkout service. This service acts as an orchestrator. It interacts with all of the different services necessary to check out a customer to manage the process of checking out, including checking inventory, billing, sending an order confirmation message, and initiating shipping the order.
- Implement the Frontend. This service should both serve the shop’s functionality as a web page, and maintain session information to distinguish different customers.
- Implement any otherwise unimplemented services that these two services require. As before, these can/should be dummy implementations, where it is sufficient to log that the operations are occurring without actually implementing them. If information from the service is required, it can serve static (unchanging) data.

## Other Requirements
- You should create GitHub repos for your new services, and add me to them (so that I can at least see your code).
- Demonstrate your (partially?) completed application running in the cloud during or prior to next week’s lab.
