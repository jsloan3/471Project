from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from .forms import *
from .models import *
from django.contrib import messages

# Create your views here.
def view_pharm(request):
    return HttpResponse('Hello World')


def home(request):
    # https://www.tutorialspoint.com/django/django_sessions.htm
    return render(request,'home.html',{'logged_in': request.session.get('username', default = None)}) # send a username forwards to the home page render (Can be None)

# Login mechanics
def login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            form_username = form.cleaned_data['username']
            form_password = form.cleaned_data['password']

            # check for customer first

            try:
                invalidCred = False
                 # https://docs.djangoproject.com/en/5.1/topics/db/queries/
                cust_user = Customer.objects.get(username = form_username)   # Syntax: <variable name> = <model name>.objects.get(<dbcolumn=value>)
                print(cust_user.first_name + ' ' + cust_user.last_name) # used for testing

                # https://www.tutorialspoint.com/django/django_sessions.htm
                request.session['username'] = form_username # save the customer username for the home page
                request.session['usertype'] = 1
                return redirect('user') # Redirect to the home site
            
            except Customer.DoesNotExist:
                messages.error(request, 'Invalid username or password')
                print("Invalid customer username")

                # check for representative
                try:
                    # invalidCred = False
                    rep_user = HealthCareRepresentative.objects.get(username = form_username)
                    print(rep_user.first_name + ' ' + rep_user.last_name)
                    request.session['username'] = form_username
                    request.session['usertype'] = 2
                    return redirect('healthrep')
                except HealthCareRepresentative.DoesNotExist:
                    # invalidCred = True
                    print("Invalid rep username")

                    # check for distributer
                    try:
                        dist_user = Distributer.objects.get(username = form_username)
                        request.session['username'] = form_username
                        request.session['usertype'] = 3
                        return redirect('distrib')
                    except Distributer.DoesNotExist:
                        invalidCred = True
                        print("Invalid distributor username")
    else:
        form = LoginForm()

    # if invalidCred:
    #     messages.error(request, "Incorrect Username/Password")

    return render(request,'login.html', {'form':form})

# A simple log out request. Reference: https://www.tutorialspoint.com/django/django_sessions.htm
def logging_out(request):
    request.session.flush() # delete the sessions cookies
    return redirect('home') # redirect to the main page

# Reference: https://docs.djangoproject.com/en/5.1/topics/forms/modelforms/
def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = SignupForm()
    return render(request,'signup.html', {'form':form})

def user(request):
    return render(request, 'user.html',{'logged_in': request.session.get('username', default = None)})

def distrib(request):
    # grab the distributer data
    dist_user = Distributer.objects.get(username = request.session['username'])
    # grab the medications associated with that distributer
    dist_medications = Medication.objects.filter(distributer_id = dist_user.distributer_id)
    # grab every inventory that stores medication that this distributor has supplied.
    dist_inventories = Inventory.objects.filter(distributer_id = dist_user.distributer_id)
    # medication ingrediants
    med_ingredients = MedicationIngredients.objects.filter(med_name__in = dist_medications)

    # filter medication ingredients further using a get request:
    #selected_med = request.GET.get('medication')
    #print(f"Selected Medication: {selected_med}")

    if request.method == 'POST':
        med_form = MedForm(request.POST)
        ing_form = IngredientForm(request.POST)
        if med_form.is_valid():
            # https://docs.djangoproject.com/en/5.1/topics/forms/modelforms/#:~:text=If%20you%20call%20save(),on%20the%20resulting%20model%20instance.
            # The form is created but not saved, we still need to input the dist id attribute
            medication = med_form.save(commit=False)
            # Although it's a foreign key of type CHAR. This is actually asking for a distributer to be assigned to.
            medication.distributer_id = dist_user
            medication.save() #Add the medication

        if ing_form.is_valid():
            ing_form.save()
    else:
        med_form = MedForm()
        ing_form = IngredientForm()
    # send over the re;evant medications for render
    return render(request,'distrib.html',
        {
            'logged_in': request.session.get('username', default = None), 
            'meds':dist_medications,
            'add_med_form':med_form,
            'add_ing_form':ing_form,
            'inventories':dist_inventories,
            'med_ingredients':med_ingredients
            #'selected_med': selected_med
        })


def healthrep(request):
    rep = request.session.get('username', default=None)
    repInstance = HealthCareRepresentative.objects.get(username=rep)
    customer_id = None
    cust = Customer.objects.filter(healthcare_rep = rep)
    successString =''
    if request.method == 'POST':
        if 'unlink_customer' in request.POST:
            customer_user = request.POST.get('customer_user')

            try:
                customer_to_unlink = Customer.objects.get(username=customer_user, healthcare_rep=repInstance)
                customer_to_unlink.healthcare_rep = None
                customer_to_unlink.save()
                messages.success(request, "Customer unlinked successfully.")

            except Customer.DoesNotExist:
                messages.error(request, "Customer not found or unauthorized unlink attempt.")
        form = LinkCustForm(request.POST)
        if form.is_valid():
            form_ABID = form.cleaned_data['AB_id']
            form_Fname = form.cleaned_data['Fname']
            form_Lname = form.cleaned_data['Lname']
            try:
                Cust = Customer.objects.get(alberta_healthcare_id=form_ABID, first_name=form_Fname, last_name=form_Lname)
                Cust.healthcare_rep = repInstance
                Cust.save()
                messages.success(request, 'Customer added successfully')
                form = LinkCustForm()
            except Customer.DoesNotExist:
                messages.error(request, "Customer doesn't exist")

    else:
        form = LinkCustForm()

    context = {'logged_in': request.session.get('username', default = None),
               'customers': cust,
               'rep': rep,
               'form': form,
              'customer_id':customer_id
               }

    return render(request, 'healthrep.html', context)

def customer_details(request, customer_username):
    custHealthID = Customer.objects.get(username=customer_username).alberta_healthcare_id
    customer = get_object_or_404(Customer, username=customer_username)

    try:
        custPhone = CustomerPhone.objects.get(alberta_healthcare_id=custHealthID).cust_phone_field
    except CustomerPhone.DoesNotExist:
        custPhone = "No phone number provided"

    try:
        custEmail = CustomerEmail.objects.get(alberta_healthcare_id=custHealthID).cust_email
    except CustomerEmail.DoesNotExist:
        custEmail = "No email provided"

    allergies = Allergy.objects.filter(cust_healthcare_id=custHealthID).select_related('ingredient_id')

    # If no allergies are found
    if not allergies.exists():
        custAllergies = {"message": "No allergies! :)"}
    else:
        custAllergies = [
            {
                "iupac_name": allergy.ingredient_id.iupac_name,
                "common_name": allergy.ingredient_id.common_name
            }
            for allergy in allergies
        ]

    try:
        custInsurance = InsurancePlan.objects.get(cust_healthcare_id=custHealthID).coverage_type
    except InsurancePlan.DoesNotExist:
        custInsurance = 'No insurance plan'

    data = {
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "phone": custPhone,
        "email": custEmail,
        "allergies": custAllergies,
        "healthcare_id": customer.alberta_healthcare_id,
        "insurance_plan": custInsurance,

    }
    return JsonResponse(data)


def edit_customer(request, username):
    customer = get_object_or_404(Customer, username=username)
    try:
        customer_phone = CustomerPhone.objects.get(alberta_healthcare_id=customer.alberta_healthcare_id)
    except CustomerPhone.DoesNotExist:
        customer_phone = None

    try:
        customer_email = CustomerEmail.objects.get(alberta_healthcare_id=customer.alberta_healthcare_id)
    except CustomerEmail.DoesNotExist:
        customer_email = None

    try:
        customer_insurance = InsurancePlan.objects.get(cust_healthcare_id=customer.alberta_healthcare_id)
    except InsurancePlan.DoesNotExist:
        customer_insurance = None

    if request.method == 'POST':
        # Handle form submission
        customer_form = CustomerEditForm(request.POST, instance=customer)
        phone_formset = CustPhoneForm(request.POST, instance=customer_phone)
        email_formset = CustomerEmailForm(request.POST, instance=customer_email)
        ins_formset = CustomerInsuranceForm(request.POST, instance=customer_insurance)


        if customer_form.is_valid() and phone_formset.is_valid() and email_formset.is_valid():
            customer_instance = customer_form.save(commit=False)
            phone_instance = phone_formset.save(commit=False)
            email_instance = email_formset.save(commit=False)
            ins_instance = ins_formset.save(commit=False)

            phone_instance.alberta_healthcare_id = customer
            email_instance.alberta_healthcare_id = customer
            ins_instance.cust_healthcare_id = customer
            # for field in customer_form.cleaned_data:
            #     if customer_form.cleaned_data[field] not in [None, ""]:
            #         setattr(customer_instance, field, customer_form.cleaned_data[field])
            #
            # for field in phone_formset.cleaned_data:
            #     if phone_formset.cleaned_data[field] not in [None, ""]:
            #         setattr(phone_instance, field, phone_formset.cleaned_data[field])
            #
            # for field in email_instance.cleaned_data:
            #     if email_formset.cleaned_data[field] not in [None, ""]:
            #         setattr(email_instance, field, email_formset.cleaned_data[field])
            # customer_instance.save()
            #
            # phone_formset.save()
            # email_formset.save()
            #
            # return redirect('customer_details', username=customer.username)
            print("Customer instance data:", customer_instance.__dict__)
            print("Phone instance data:", phone_instance.__dict__)
            print("Email instance data:", email_instance.__dict__)
            print("Insurance instance data:", ins_instance.__dict__)
            customer_form.save()
            phone_formset.save()
            email_formset.save()
            ins_formset.save()

            return redirect('/healthrep')
    else:
        # Populate forms with existing data
        customer_form = CustomerEditForm(instance=customer)
        phone_formset = CustPhoneForm(instance=customer_phone)
        email_formset = CustomerEmailForm(instance=customer_email)
        ins_formset = CustomerInsuranceForm(instance=customer_insurance)

    return render(request, 'edit_customer.html', {
        'customer_form': customer_form,
        'phone_formset': phone_formset,
        'email_formset': email_formset,
        'ins_formset': ins_formset,
        'customer': customer,
    })